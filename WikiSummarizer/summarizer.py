import wikipedia as wiki
import nltk
import re
import heapq

class WikiSummarizer:
    def __init__(self):
        self.stop_words = nltk.corpus.stopwords.words('english')
        self.ps = nltk.stem.PorterStemmer()

    def __getWikiArticle(self, topic):
        wikisearch = wiki.page(topic)
        article_text = wikisearch.content 
        formatted_article_text = re.sub(r'\[[0-9]*\]', ' ', article_text) 
        formatted_article_text = re.sub(r'\s+', ' ', formatted_article_text)
        formatted_article_text = re.sub(r'^=+\s+.*\s+=+$', '', formatted_article_text)
        return formatted_article_text
    
    def __calculateSentenceScores(self, formatted_article_text, sent_lim=30):
        sentence_list = nltk.sent_tokenize(formatted_article_text)
        
        word_frequencies = {}
        for word in nltk.word_tokenize(formatted_article_text):
            word = self.ps.stem(word)
            if word not in self.stop_words:
                if word not in word_frequencies.keys():
                    word_frequencies[word] = 1
                else:
                    word_frequencies[word] += 1
        
        maximum_frequency = max(word_frequencies.values())

        for word in word_frequencies.keys():
            word_frequencies[word] = (word_frequencies[word]/maximum_frequency)
        
        sentence_scores = {}
        for sent in sentence_list:
            for word in nltk.word_tokenize(sent.lower()):
                if word in word_frequencies.keys():
                    if len(sent.split(' ')) < sent_lim:
                        if sent not in sentence_scores.keys():
                            sentence_scores[sent] = word_frequencies[word]
                        else:
                            sentence_scores[sent] += word_frequencies[word]
        
        return sentence_scores
    
    def getSummary(self, topic, num_sent=7, sent_lim=30):
        article = self.__getWikiArticle(topic)
        sentence_scores = self.__calculateSentenceScores(article, sent_lim)
        summary_sentences = heapq.nlargest(num_sent, sentence_scores, key=sentence_scores.get)
        summary = ' '.join(summary_sentences)
        return summary