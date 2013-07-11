## 
## Glue between Synapse and BitMill 
## https://sagebionetworks.jira.com/browse/PLFM-1954
##
#  set the environment variables:
#    AWS_ACCESS_KEY_ID_<i> (i=1,2..) - AWS Access Key ID for the AWS user that can create buckets and IAM users
#    AWS_SECRET_ACCESS_KEY_<i> (i=1,2..) - AWS Secret Access Key for the AWS user that can create buckets and IAM users
#    EVALUATION_ID 
#    NUMERATE_BUCKET_ACCESS_EMAIL_ADDRESS
#    SYNAPSE_USER_ID
#    SYNAPSE_USER_PW
#    SNS_TOPIC
#

##
from synapseclient import Synapse
from synapseclient import File
from os import environ
from os import remove
from boto.iam.connection import IAMConnection
from boto.s3.connection import S3Connection
from boto.sns import SNSConnection
from json import dumps
from createUserNameMod import createUserName
from awsUtil import *
import logging

logging.basicConfig(filename="synBitMillGlue.log", level=logging.DEBUG)

evaluationId = environ['EVALUATION_ID']
numerateBucketAccessEmailAddress= environ['NUMERATE_BUCKET_ACCESS_EMAIL_ADDRESS']
synapseUserId = environ['SYNAPSE_USER_ID']
synapseUserPw = environ['SYNAPSE_USER_PW']
snsTopic = environ['SNS_TOPIC']
# we allow multiple AWS accounts.  this gets us past the 100 bucket per account limit
synapseAccessKeyProjectId=environ["SYNAPSE_ACCESS_KEY_PROJECT_ID"]

s3Connections = []
iamConnections = []
i=0
while True:
    aws_access_key_id = environ.get("AWS_ACCESS_KEY_ID_"+str(i+1))
    aws_secret_access_key = environ.get("AWS_SECRET_ACCESS_KEY_"+str(i+1))
    if (i==0):
        snsConnection = SNSConnection(aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

    if ((aws_access_key_id is None) or (aws_secret_access_key is None)):
        break
    else:
        s3Connections.append(S3Connection(aws_access_key_id, aws_secret_access_key))
        iamConnections.append(IAMConnection(aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key))
        i=i+1
        
if (len(s3Connections)==0):
    raise("No AWS crdentials provided")

MAXIMUM_USER_NAME_LENGTH = 63

## connect to Synapse
syn = Synapse()
syn.login(synapseUserId, synapseUserPw)
ownUserProfile = syn.getUserProfile()
ownPrincipalId = ownUserProfile['ownerId']

## get all Participants for Evaluation
participants = syn.restGET("/evaluation/"+evaluationId+'/participant?limit=99999')['results']
print "total number of results: "+str(len(participants))

## For each participant
participantList = []
anyNewUsers = False
for i,part in enumerate(participants):
    ## add to a list the user's first name, last name, email address, user name and principal ID
    ## "user name" is defined as <firstName>.<lastName>.<principalId>.wcpe.sagebase.org
    partId = part['userId']
    up = syn.getUserProfile(partId)
    # scrub for illegal characters, control string length, convert to lower case
    userName = createUserName(up['firstName'], up['lastName'], partId, MAXIMUM_USER_NAME_LENGTH)
    participantList.append({'firstName':up['firstName'], 'lastName':up['lastName'], 'email':up['email'], 'userName':userName, 'bucketName':userName, 'principalId':partId})
    print userName
    
    # Ensure user exists
    ## Create a IAM user for that participant's aws account.
    indexOfAccountForUser = findUser(userName, iamConnections)
    if (indexOfAccountForUser<0):
        # user does not exist
        anyNewUsers=True
        print "\t"+userName+" is a new user"
        # need to create user in an account that can accommodate a new bucket
        indexOfAccountForUser = findBucketSpace(s3Connections)
        if (indexOfAccountForUser<0):
            raise("No account has room for a new bucket!")
        iamConnections[indexOfAccountForUser].create_user(userName)
    else:
        user = iamConnections[indexOfAccountForUser].get_user(userName)
    iamConnection = iamConnections[indexOfAccountForUser]
    s3Connection = s3Connections[indexOfAccountForUser]
        
   
    # Set user policy
    ## Give the user access to the bucket
    policy_json = "{\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"s3:*\",\"Resource\":[\"arn:aws:s3:::"+userName+"\",\"arn:aws:s3:::"+userName+"/*\"]}]}"
    iamConnection.put_user_policy(userName, userName+"_policy", policy_json)
   
    # Ensure bucket exists
    ## has the user's bucket already been created in S3?
    userBucket = s3Connection.lookup(userName)
    if userBucket is None:
        anyNewUsers=True  
        print "\t"+userName+" is a new user"
        ## Create a bucket for that user in the same account
        userBucket = s3Connection.create_bucket(userName)
        ## Grant a Numerate IAM user full control of the bucket. 
        userBucket = userBucket.add_email_grant("FULL_CONTROL", numerateBucketAccessEmailAddress)
    
    
    # Ensure credentials exist
    ## get or create an access key
    allKeys = iamConnection.get_all_access_keys(userName)
    alreadyHasKey = (len(allKeys['list_access_keys_response']['list_access_keys_result']['access_key_metadata'])>0)
    ## if there isn't a key already, then create one and upload it to Synapse
    if not alreadyHasKey:
        print "\tcreating access credentials for "+userName
        ## Create a key
        accessKey = iamConnection.create_access_key(userName)
        accessKeyId = accessKey['create_access_key_response']['create_access_key_result']['access_key']['access_key_id']
        secretAccessKey = accessKey['create_access_key_response']['create_access_key_result']['access_key']['secret_access_key']
        ## Write to a local, temporary file
        fileName = userName
        try:
            remove(fileName)
        except:
            ## do nothing
            pass
        f = open(fileName, 'w')
        f.write("The following credentials provide access to the AWS S3 bucket: "+userName+"\n")
        f.write('accessKeyId: '+accessKeyId+'\n')
        f.write('secretAccessKey: '+secretAccessKey+'\n')
        f.close()
        ## Upload the file to Synapse
        synapseFile = File(fileName, parentId=synapseAccessKeyProjectId)
        synapseFile = syn.store(synapseFile)
        ## clean up the temporary file
        remove(fileName)
        ## create the ACL, giving the user 'read' access (and the admin ALL access)
        acl = {"resourceAccess":[{"accessType":["READ"],"principalId":partId},  \
                        {"accessType": ["CHANGE_PERMISSIONS", "DELETE", "CREATE", "UPDATE", "READ"], "principalId":ownPrincipalId}]}
        syn._storeACL(synapseFile.id, acl)
         
## 
## Send to an SNS topic the list of Participants, including bucket id. 
##
batchSize = 8
start = 0
while (start<len(participantList)):
    message = dumps(participantList[start:(start+batchSize)], indent=2)
    if anyNewUsers:
        snsConnection.publish(topic=snsTopic, message=message, subject="WCPE Participant List")
    else:
        print "No new users, so participant list will not be sent. Message content _would_ be:"
        print message
        print ""
    start += batchSize

    