'''
Author  :  Apurba Paul
Team    :  Cloud Guardians
Purpose :  TO Run a Lambda Script which is invoked by autoscaling Lifehook for Event:Terminating wait state; 
           ssh into the instance and copy logs to bb-logs and complete the lifecycle action; terminate the instance 
'''
import boto3
import json
import paramiko

def lambda_handler(event, context):
    # retrieve instance id from event
    print "Getting Instance id of terminating event"
    message = json.loads(event['Records'][0]['Sns']['Message'])
    detail = message["detail"] 
    InstId = detail["EC2InstanceId"]
    LifeHookName = detail["LifecycleHookName"]
    AutoScaGrpName = detail["AutoScalingGroupName"]
    LifeActionToken = detail["LifecycleActionToken"]
    print "Instance ID of terminating wait event:" + str(InstId)
    pubIpAddr = getPubIp(InstId)
    getkeyS3()
    runScript(pubIpAddr)
    terminateInstances(LifeHookName,AutoScaGrpName,LifeActionToken,InstId)

# filter instance from all instances using instance id as filter
# retrieve public ip address for instance id
def getPubIp(InstId):
    print "Getting  Public IP Address of Instance"
    client = boto3.client('ec2')
    instDict = client.describe_instances(InstanceIds=[InstId]) 
    for r in instDict['Reservations']:
        for i in r['Instances']:
            pubIpAddr = i['PublicIpAddress']
    print "Public Ip address of instance: " + InstId + " is: " + pubIpAddr         
    return pubIpAddr        

# get pem key from s3 bucket
def getkeyS3():
    print "Getting private key from S3 bucket"
    #try:
    s3_client = boto3.client('s3')
    s3_client.download_file('bb-keys','bbadmin-minjar.pem','/tmp/bbadmin-minjar.pem')
    print "Key downloaded in /tmp/ as bbadmin-minjar.pem file"        
    
# ssh into instance server(key, username, public Ip)
# run a rsync sript already existing in the server
def runScript(pubIpAddr):
    print "Logging into server with necessary inputs" 
    key_path = paramiko.RSAKey.from_private_key_file('/tmp/bbadmin-minjar.pem')
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(hostname = pubIpAddr, username = "bbadmin", pkey = key_path)
    print "Connected to " + pubIpAddr
    command = 'if [ -z "$(pgrep rsync)" ]; then sh /srv/webapps/bigbasket.com/BigBasket/jobs/hourly_rsync_logs.sh; else while [ ! -z "$(pgrep rsync)" ]; do echo "Rsync process currently running: sleep now"; sleep 30; done fi'
    print "Executing {}".format(command)
    stdin, stdout, stderr = c.exec_command(command)
    print stdout.read()
    print stderr.read()
    
# Terminate instances after script is run 
def terminateInstances(LifeHookName,AutoScaGrpName,LifeActionToken,InstId):
    print "Terminating instance: " + InstId
    client = boto3.client('autoscaling')
    print "AutoScaling Complete Life Cycle Action "
    # LifeActionResult = "CONTINUE"
    # response = client.complete_lifecycle_action(LifeHookName,AutoScaGrpName,LifeActionToken,LifeActionResult,InstId)
    response = client.complete_lifecycle_action(LifecycleHookName=LifeHookName,
    AutoScalingGroupName=AutoScaGrpName,
    LifecycleActionToken=LifeActionToken,
    LifecycleActionResult='CONTINUE',
    InstanceId=InstId)
    # print response 
    print "AutoSCaling LifeCycle Action: Terminate Proceed"