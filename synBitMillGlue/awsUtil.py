'''
Created on Jul 11, 2013

@author: brucehoff
'''

from boto.exception import BotoServerError

# Given an array of S3 Connections, returns the index of the one having room
# for another bucket, or -1 if no account has room
def findBucketSpace(s3Connections):
    for i,s3Connection in enumerate(s3Connections) :
        if (len(s3Connection.get_all_buckets())<95):  # actual limit is 100, but this gives us 'wiggle room'
            return(i)
    return -1

# Given a user name and an array of IAM Connections, returns the index of the one
# containing the user, or None if the user doesn't exist
def findUser(userName, iamConnections):
    for i,iamConnection in enumerate(iamConnections) :
        try:
            iamConnection.get_user(userName)
            return(i)
        except BotoServerError:
            # user does not exist
            pass

    return -1 