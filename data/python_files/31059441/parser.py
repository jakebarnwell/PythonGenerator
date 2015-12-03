import sys
import urllib
from urllib import urlencode, urlopen
import re
from datetime import datetime
from dateutil.parser import parse
from time import sleep


translate_url = "http://api.microsofttranslator.com/V2/Http.svc/Translate"
detect_url = "http://api.microsofttranslator.com/V2/Http.svc/Detect"

language_list = ['ar', 'cs', 'da', 'de', 'en', 'et', 'fi', 'fr', 'nl', 'el', 'he', 'ht', 'hu', 'id', 'it', 'ja', 'ko', 'lt', 'lv', 'no', 'pl', 'pt', 'ro', 'es', 'ru', 'sk', 'sl', 'sv', 'th', 'tr', 'uk', 'vi', 'zh-CHS', 'zh-CHT', ]

appId = 'blablabla' # Substitute into your bing app id

def detect(sentence):
    return 'en'
    args = {'appId': appId,
            'text': sentence}
    url = detect_url + '?' + urlencode(args)
    raw_result = urlopen(url).read()
    raw_lang = re.match('<string.*>(.*)<\/string>', raw_result).groups()[0]
    result = gettranslate(sentence, raw_lang)
    #print raw_lang, result
    if not result:
        for lang in language_list:
            result = gettranslate(sentence, lang)
            print result
            if result:
                return lang
    return raw_lang

def gettranslate(sentence, lang):
    if lang == 'en':
        return sentence
    args = {'appId': appId,
            'from': lang,
            'to': 'en',
            'text': sentence}
    url = translate_url + '?' + urlencode(args)
    raw_result = urlopen(url).read()
    #print raw_result
    try:
        return re.match('<string.*>(.*)<\/string>', raw_result).groups()[0]
    except Exception:
        return None

def parse_end(content):
    for index in range(len(content) - 1, -1, -1):
        if content[index] != ' ':
            return content[:index + 1]

def parse_beginning(content):
    for index in range(0, len(content)):
        if content[index] != ' ':
            return content[index:]

def parse_date(content):
    if content.endswith('00:00:00'):
        return content[:-9]
    return content



def try_result(try_type, lang, content, start, length, word_list=None):
    if try_type == 'other':
        partial_sentence = ' '.join(word_list[start:start+length])
        result = gettranslate(partial_sentence, lang)
        if result.startswith('on') \
        or result.startswith('at') \
        or result.startswith('in') \
        or result.startswith('until'):
            return None
        try:
            date = parse(result)
            #print partial_sentence
            first_word = word_list[start]
            last_word = word_list[start+length-1]
            start_pos = content.find(first_word)
            end_pos = content.find(last_word) + len(last_word)
            #print content[start_pos:end_pos]
            #print parse_end(content[:start_pos])
            return parse_end(content[:start_pos]) + '|' + parse_date(str(date)) + '|' + parse_beginning(content[end_pos:])
        except Exception as e:
            #print e
            return None
    else:
        partial_sentence = content[start:start+length]
        result = gettranslate(partial_sentence, lang)
        #print start, start + length, partial_sentence, result
        if result.startswith('on') \
        or result.startswith('at') \
        or result.startswith('in') \
        or result.startswith('until'):
            return None
        try:
            date = parse(result)
            #print partial_sentence
            start_pos, end_pos = start, start + length
            #print content[start_pos:end_pos]
            #print parse_end(content[:start_pos])
            return parse_end(content[:start_pos]) + '|' + parse_date(str(date)) + '|' + parse_beginning(content[end_pos:])
        except Exception as e:
            #print e
            return None

def parsedate(content):
    lang = detect(content)
    #print lang
    if lang in ['ja', 'zh-CHS', 'zh-CHT']:
        return None
        for length in range(len(content), 0, -1):
            for start in range(0, len(content) - length + 1):   
                result = try_result('particular', lang, content, start, length, None)
                if result:
                    return result

    word_list = re.split('[ !\?\(\)\[\]]', content)
    word_list = [w for w in word_list if w]
    
    for length in range(len(word_list), 0, -1):
        for start in range(0, len(word_list) - length + 1):
            result = try_result('other', lang, content, start, length, word_list)
            if result:
                return result

def main():
    try:
        file_name = sys.argv[1]
    except Exception:
        file_name = 'datesentences.txt'
    file_content = open(file_name).read().split('\n')
    for content in file_content:
        if content:
            #print content.split()
            try:
                print parsedate(content)
            except Exception as e:
                print e
            sleep(1)

if __name__ == '__main__':
    main()
