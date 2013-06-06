'''
Created on Jun 6, 2013

@author: brucehoff
'''

import re

def scrubString(s):
    "This removes any chars not letters, numbers, periods, dashes, or underscores"
    return re.sub("[^\w\._-]", "", s)

def createUserName(firstName, lastName, principalIdString, maxUserNameLength):
    "Returns a string of the form <firstName>.<lastName>.<principalIdString>.wcpe.sagebase.org, scrubbing and truncating names if necessary."
    scrubbedFirstName = scrubString(firstName.lower())
    scrubbedLastName = scrubString(lastName.lower())
    suffix = principalIdString + ".wcpe.sagebase.org"
    remainingChars = maxUserNameLength - len(suffix)
    if (remainingChars<0): 
        raise Exception("Principal ID String is too long: "+principalIdString)
    if (remainingChars<=1): 
        return suffix
    # have at least two characters left
    suffix = "." + suffix
    remainingChars = maxUserNameLength - len(suffix)
    # now I know remainingChars is at least 1
    if (len(scrubbedLastName)>remainingChars-2):
        return scrubbedLastName[:remainingChars] + suffix
    suffix = "." + scrubbedLastName + suffix
    remainingChars = maxUserNameLength - len(suffix)
    # we know that remainingChars is at least 1
    return scrubbedFirstName[:remainingChars] + suffix
    
        
    
    