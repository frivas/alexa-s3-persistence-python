# S3 Data Persistence for ASK SDK for Python (v1.5.0)

# Some background
A few days ago I came to know, through [German Viscuso’s](https://twitter.com/germanviscuso) [tweet](https://twitter.com/germanviscuso/status/1081198187954794496), that the ASK SDK for NodeJS supports data persistence in S3. It is not supported by ASK SDK for Python yet. 

I thought it is a nice feature to have and decided to check the documentation of ASK SDK for Python and did not found something similar to what German showed. I thought of giving it a try and in this short article I am going to describe how a possible implementation of this feature can be done using, or reusing I should day, already existent SDK features.

**Disclaimer: This is not officially supported. Use it at your own risk. The implementation can be improve, definitely. I wrote a very short proposal as a feature request in** [ASK SDK for Python Data Persistence in S3](https://github.com/alexa/alexa-skills-kit-sdk-for-python/issues/57). 

# In this article you will find:
- A description of the module S3 Persistence for the ASK SDK for Python.
- Instructions to get this module working in your skill.
- Further comments

# Description of the module
This module consists of 3 files. I like to think of it as a pluggable module as just copying and pasting the files in the right place will get you up and running quickly.

This module uses ```Boto 3``` library. It already comes with the ASK SDK.

The data is persisted as a JSON.

I took some ideas from the SDK for NodeJS where this is already implemented and figured out how it works with the example German coded. For example, the structure of the module was taken from both SDKs (for NodeJS and Python).

## The persistence module
It works like the current DynamoDB Persistence one. It consists in 2 files:
- The adapter, which I called: ```S3PersistenceAdapter```
- The object key generator, which I called ```ObjectKeyGenerators```

If we check the DynamoDB one, you will notice it is (mostly) the same:

```bash
✗ ls -1
__init__.py
__version__.py
adapter.py
partition_keygen.py
```

I have placed both files in ```ask_sdk_s3_persistence``` directory.

### How ```S3PersistenceAdapter``` works
First of all the class ```S3PersistenceAdapter``` derives from ```AbstractPersistenceAdapter``` like the DynamoDB one. 

The constructor in this case, unlike the DynamoDB one, takes different parameters:

```python
    def __init__(self, bucket_name, object_generator, 
                 s3_client=boto3.client('s3'), path_prefix=None):
```

```bucket_name```: is the name of the bucket were you will store the json file that contains the data you want to persist. This bucket has to be created beforehand as well as all the right permissions to your execution role and your Lambda function to access S3.

```object_generator```: This is used to distinguish later on each to whom the data belongs to. The file that is created to store the data uses the information obtained from this generator. More on this later in the article.

```s3_client```: In this case is straight forward, S3 Client.

```path_prefix```: This is used when there is some directory structure in your bucket, for example, if you want to have a directory per customer or per skill.

Deriving from ```AbrstractPersistenceAdapter``` means that we have to implement 2 methods that will support the basic ```get``` and ```set``` features: 

#### ```get_attributes(self, request_envelope)```
This method takes the ```request_envelope``` as parameter. A call to the `object_generator` function passing that ```request_envelope``` will return an ```id``` that joined with the ```path_prefix``` will be used to create an ```objectId``` which is basically the location and the name of the file where the data will be stored. Then it tries to get that object from S3 using the ```get_object``` method. If it is not possible then it will create a new one with the creating timestamp in a tag called ```created```. Then it returns the object in any case. 


#### ```save_attributes(self, request_envelope, attributes)```
This method takes the ```request_envelope``` and the ```attributes``` to be stored. Like the ```get_attributes``` method it, first, creates the ```objectId```. Then takes the attributes dictionary and converts it to bytes and finally creates the object in S3 using ```put_object```.

In both methods some exceptions and errors are handled.

### How ```ObjectKeyGenerators``` works
This is basically a set of functions that extract the ```user_id```, ```device_id``` or ```application_id``` from the request envelope.

Is it really needed?, probably not, however it keeps the code organised and easy to maintain. 

As an additional comment: the example from German includes a function to extract the ```application_id```, I wonder why it is not included in the ```ObjectKeyGenerators``` from NodeJS’ SDK. Seems like a nice proposal.

## New ```standard_s3.py```
The SDK comes with a class called ```StandardSkillBuilder``` that lives in ```standard.py```. It derives from ```SkillBuilder```. After thinking a bit about this, I wanted the S3 Persistence module to be, kind of, pluggable so that is why this I decided to create ```standard_s3.py```. It also derives from ```SkillBuilder``` so it requires a ```skill_configuration``` that is created based on the parameters the constructor receives. It takes basically the same parameters as the S3 Persistence Adapter, as follows:

```python
    def __init__(self, bucket_name=None, s3_client=None,
                 object_generator=None, path_prefix=None):
```

# How to use this module - Instructions
1. Grab a copy of the files from my GH repository [here](https://github.com/frivas/alexa-s3-persistence-python/tree/master/lambda/eu-west-1_TestS3) you can also clone the repo and try the sample skill yourself. Thanks German for the idea. The sample skill is the same proposed by German in his example.

**In case you wonder which files:**

- [This directory](https://github.com/frivas/alexa-s3-persistence-python/tree/master/lambda/eu-west-1_TestS3/ask_sdk_s3_persistence) and place it in the root directory right where the rest of the SDK modules are.

- [This file](https://github.com/frivas/alexa-s3-persistence-python/blob/master/lambda/eu-west-1_TestS3/ask_sdk/standard_s3.py) and place it in ```ask_sdk``` right where ```standard.py``` is.

2. In your main skill file (or lambda) add this:

```python
from ask_sdk.standard_s3 import StandardSkillBuilder
from ask_sdk_s3_persistence.ObjectKeyGenerators import applicationId
```

*Note: When it comes to the ```ObjectKeyGenerators``` use any of the available, that is up to you, remember that it will be the name of the file where the data will be stored. I have used ```applicationId``` to be consistent with the sample skill written by German.*

3. Also add this:

```python
s3_client = boto3.client('s3') # a
path_prefix = 'test_prefix' # b

ssb = StandardSkillBuilder(bucket_name='<bucket_name>', object_generator=applicationId, s3_client=s3_client, path_prefix=path_prefix) # c
```

a) Is the S3 Client. I know, self-explanatory. :)

b) In case you have some folder structure in your bucket, otherwise leave it empty.

c) Create a new ```StandardSkillBuilder``` passing the name of the bucket, the object key generator, the client and path prefix (if used) to it.

4. As you may notice in the sample skill file [index.py](https://github.com/frivas/alexa-s3-persistence-python/blob/master/lambda/eu-west-1_TestS3/index.py) I have included 2 interceptors (quest and response) that will take care of loading and saving the data based on  those events. When ```Response``` one saves the data and when ```Request``` another loads it. Both can be modified as per your particular needs. This is just a sample.


# Further thoughts

- A better error/exception handling is needed.
- There is an S3 Transfer module that comes with Boto 3, not sure if it would be better to use the methods that come with it somehow.
- The ```standard.py``` and ```standard_s3.py``` can be merged to have a generic ```StandarSkillBuilder(*args)```.
- An improvement on the ```get_attributes``` method that avoids storing dummy data can be very nice.
- Include tests.
