from __future__ import absolute_import

"""
Analyze the tweet and try to figure out what the user means
Before analyzing you have to clean the data
"""

# import regex
import re

# import csv read_raw_tweets_from_cassandra
import csv

# import nltk
import nltk

from proj.celery import app

import pycassa

# ininialize Cassandra connection pool

pool = pycassa.ConnectionPool('tweets') # we can then use this connection pool to connect to Cassandra

domain_recongition_classifier = None
issue_recognition_classifier = None

domain_feature_list = []
issue_feature_list = []

def cleanTweet(tweet_text):
    # Convert to lower case
    tweet_text = tweet_text.lower()
    # Convert www.* or https?://* to URL
    tweet_text = re.sub('((www\.[^\s]+)|(https?://[^\s]+))','URL',tweet_text)
    # Convert @username to AT_USER
    tweet_text = re.sub('@[^\s]+','AT_USER',tweet_text)
    #Remove additional white spaces
    tweet_text = re.sub('[\s]+', ' ', tweet_text)
    #Replace #word with word
    tweet_text = re.sub(r'#([^\s]+)', r'\1', tweet_text)
    #trim
    tweet_text = tweet_text.strip('\'"')
    print 'tweet pre-processed:'
    print tweet_text
    return tweet_text

# look for 2 or more repetitions of character and replace with the character itself
def replaceTwoOrMore(word):
    pattern = re.compile(r"(.)\1{1,}", re.DOTALL)
    return pattern.sub(r"\1\1", word)

def getFeaturevector(tweet_text):
    feature_vector = []
    words = tweet_text.split()
    for word in words:
        word = replaceTwoOrMore(word=word)
        # strip out punctuation
        word = word.strip('\'"?,.')
        # check if the word stats with an alphabet
        # TODO: find out if this works for Swahili
        # val = re.search(r"^[a-zA-Z][a-zA-Z0-9]*$", word)
        # TODO: Add list of stop words that don't add meaning to the feature vector
        feature_vector.append(word.lower())
    return feature_vector

# use this to extract features of a domain
def domainExtractFeatures(feature_vector):
    tweet_words = set(feature_vector)  # remove duplicate vectors from tweet
    features = {}
    # print 'showing domain list:'
    # print domain_feature_list
    for word in domain_feature_list:
        domain = None
        # print 'searh for word below in domain list:'
        # print word[0]
        if word[0] in tweet_words:
            # print 'word found'
            domain = word[1]  # if keyword is mentioned in tweet words, add it to as a mentioned category
        else:
            # print 'word not found'
            domain = 'toanalyze' # if it wasn't mentioned then, we put it in the undefined category
        features['domain mention (%s)' % word[0]] = domain # find out if the set contains the words in the domain feature list
    return features

def getDomainRecognitionList():
    domain_keywords_csv = open('proj/domain_keywords.csv', "rb")
    reader = csv.reader(domain_keywords_csv)

    domain_list = [] # tuple containing a word and its domain

    # specific for electricity
    # TODO: Switch to a more generalized csv file, that will work for new domains
    for row in reader:
        if row[0] is not None:
            if row[0] != "":
                domain_list.append((row[0],'electricity'))
        if row[1] is not None:
            if row[1] != "":
                domain_list.append((row[1],'water'))
    print 'Domain list:'
    print domain_list
    return domain_list

def getDommainRecognitionTrainingSet():
    # TODO: Read data from domain_training_set.csv, pass it to you extractor & use that information and results to train your classifier

    domain_training_set_csv = open('proj/domain_training_set.csv',"rb")
    reader = csv.reader(domain_training_set_csv)

    training_set = []  # training set is a list of tuples (features, 'result')

    for row in reader:
        cleaned_tweet_text = cleanTweet(tweet_text=row[0])
        feature_vector = getFeaturevector(tweet_text=cleaned_tweet_text)
        training_set.append((domainExtractFeatures(feature_vector=feature_vector), row[1]))  # result of feature extraction, & expected result

    return training_set

# to train the naive bayes algorithm, you need a tuple:
    # (dictionary, label)

#initialize lists and classifiers in memory

domain_feature_list = getDomainRecognitionList()
domain_recongition_classifier = nltk.NaiveBayesClassifier.train(getDommainRecognitionTrainingSet())


def getIssueRecognitionList():
    pass

def getIssueRecognitionTrainingSet():
    pass

@app.task
def analyzeTweet(tweet):
    print 'about to analyze tweet'
    cleaned_tweet_text = cleanTweet(tweet_text=tweet['text'])
    feature_vector = getFeaturevector(tweet_text=cleaned_tweet_text)
    print 'Showing domain features:'
    print domainExtractFeatures(feature_vector=feature_vector)
    print 'Showing classifier output:'
    classify_result = domain_recongition_classifier.classify(domainExtractFeatures(feature_vector=feature_vector))
    print classify_result
    if classify_result == "toanalyze":
        cf_analyzedtweets_toanalyze = pycassa.ColumnFamily(pool, 'analyzedtweets_toanalyze')
        cf_analyzedtweets_toanalyze.insert(tweet['id_str'], {'tweet_text': tweet['text'],'tweet_timestamp': int(tweet['timestamp_ms'][:-3]), 'user_screen_name': tweet['user']['screen_name'], 'tweet_category': classify_result})
    else:
        cf_analyzedtweets_tweetcategory = pycassa.ColumnFamily(pool, 'analyzedtweets_tweetcategory')
        cf_analyzedtweets_tweetcategory.insert(tweet['id_str'], {'tweet_text': tweet['text'],'tweet_timestamp': int(tweet['timestamp_ms'][:-3]), 'user_screen_name': tweet['user']['screen_name'], 'tweet_category': classify_result})

def sentimentAnalysis(tweet):
    pass

# finds out whether this is a water or electricty issue
def issueCategorization():
    pass

# finds out what time the issue occured
def issueTimeCategorization():
    pass

    # finds out where this issue occured
def issuePlaceRecognition():
    pass

    # finds out where/who to direct the issue to
def organizationMatcher():
    pass
