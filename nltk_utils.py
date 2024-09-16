import numpy as np
import nltk
from nltk.stem.snowball import FrenchStemmer
from nltk.corpus import stopwords

# Télécharger les ressources nécessaires (décommenter si nécessaire)
# nltk.download('punkt')
# nltk.download('stopwords')

stemmer = FrenchStemmer()
stop_words = set(stopwords.words('french'))

def tokenize(sentence):
    """
    Divise une phrase en tokens/mots
    """
    return nltk.word_tokenize(sentence, language='french')

def stem(word):
    """
    Trouve la racine du mot
    """
    return stemmer.stem(word.lower())

def bag_of_words(tokenized_sentence, words):
    """
    Retourne le bag of words : tableau de 1 ou 0 pour chaque mot connu
    """
    sentence_words = [stem(word) for word in tokenized_sentence if word not in stop_words]
    bag = np.zeros(len(words), dtype=np.float32)
    for idx, w in enumerate(words):
        if w in sentence_words:
            bag[idx] = 1

    return bag
