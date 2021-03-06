import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import math
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse.linalg import svds
from sklearn.preprocessing import normalize
import json
import nltk
nltk.download('wordnet')
from nltk.corpus import wordnet as wn
#import gensim
#from gensim.models import KeyedVectors
#print("loading word2vec model")
#model = KeyedVectors.load_word2vec_format("glove.6B.50d.txt.zip", binary=False)
#print('finished loading model')

df = pd.read_csv('tripadvisor_merged.csv')
with open('review_quote_world.json') as json_file:
    review_js = json.load(json_file)
review_museum = (review_js.keys())

desc_data = []
for d in df['Description']:
    if (isinstance(d, float)):
        if (math.isnan(d)):
            desc_data.append('')
    else:
        desc_data.append(d)
pure_desc = desc_data.copy()

m_index_to_name = {
    index: m_name
    for index, m_name in enumerate(df['MuseumName'])
}

m_index_to_address = {
    index: m_name
    for index, m_name in enumerate(df['Address'])
}

m_index_to_lat = {index: m_name for index, m_name in enumerate(df['Latitude'])}
m_index_to_lng = {
    index: m_name
    for index, m_name in enumerate(df['Langtitude'])
}
m_name_to_index = dict((v, k) for k, v in m_index_to_name.items())

m_index_to_country = {
    index: m_name 
    for index, m_name in enumerate(df['Country'])
}

for m in review_museum:
    ind = m_name_to_index[m]
    for review in review_js[m]:
        desc_data[ind] = desc_data[ind] + " " + review

for tag in list(df.columns)[17:200]:
    for m in review_museum:
        ind = m_name_to_index[m]
        if df[tag][ind] == 1:
            desc_data[ind] = desc_data[ind] + " " + tag.lower()

m_index_to_description = {index: desc for index, desc in enumerate(pure_desc)}

# image stuff
link = "https://source.unsplash.com/1600x900/?"
map_link = 'https://maps.googleapis.com/maps/api/staticmap?center='
api_key = 'AIzaSyDT6KA7EEHqCzX8UZgEEXIJ2Uo3O-EmWao'
other_link = '&zoom=12&size=600x400'


def get_sim_words(word):
    sim_words = []
    for ss in wn.synsets(word):
        for word in ss.lemma_names():
            sim_words.append(word)
    sim_words = list(dict.fromkeys(sim_words))
    #return sim_words
    #for (word,num) in model.similar_by_vector(model[word], topn=10, restrict_vocab=None):
    #	sim_words.append(word)
    #return sim_words


def build_vectorizer(max_features, stop_words, max_df=0.8, min_df=1,
                     norm='l2'):
    return TfidfVectorizer(stop_words=stop_words,
                           max_df=max_df,
                           min_df=min_df,
                           max_features=max_features,
                           norm=norm)


def get_sim(query, doc_index, doc_by_vocab):
    return cosine_similarity(query, doc_by_vocab)


def closest_projects(docs_compressed, project_index_in, k=5):
    sims = docs_compressed.dot(docs_compressed[project_index_in, :])
    asort = np.argsort(-sims)[:k + 1]
    # return [(m_index_to_name[i], sims[i] / sims[asort[0]],
    #          m_index_to_description[i]) for i in asort[1:]]
    #changed so it only returns the title for now
    closest_projects = []
    for i in asort[1:]:
        project = [
            m_index_to_name[i],
            "../?search=" + m_index_to_name[i].lower().replace(" ", "+")
        ]
        closest_projects.append(project)
    return closest_projects


def museum_match(q):

    vectorizer = build_vectorizer(5000, "english")
    doc_by_vocab = vectorizer.fit_transform(desc_data).transpose()

    words_compressed, _, docs_compressed = svds(doc_by_vocab, k=40)
    docs_compressed = docs_compressed.transpose()

    docs_compressed = normalize(docs_compressed, axis=1)

    return closest_projects(docs_compressed, m_name_to_index[q], 5)


def get_suggestions(q,us_only):
    vectorizer = build_vectorizer(5000, "english")
    doc_by_vocab = vectorizer.fit_transform(desc_data)
    query = vectorizer.transform([q])
    sim = get_sim(query, 5, doc_by_vocab)[0]
    top_5_idx = np.argsort(sim)[-5:]
    top_5 = []
    
    for i in reversed(top_5_idx):
        
        if (sim[i] > 0 and m_index_to_description[i] != '' ):
            if (us_only == "on" and m_index_to_country[i] == "USA" or us_only == None):
                keyword = m_index_to_name[i].split()
                if m_index_to_name[i] in review_museum:
                    if len(review_js[m_index_to_name[i]]) >= 3:
                        reviews = review_js[m_index_to_name[i]][:3]
                    else:
                        reviews = review_js[m_index_to_name[i]]
                else:
                    reviews = []
                top_5.append(
                    (m_index_to_name[i], sim[i], m_index_to_description[i],
                    link + 'museum,' + keyword[0] + ',' + keyword[-1],
                    museum_match(m_index_to_name[i]), m_index_to_address[i],
                    map_link + str(m_index_to_lat[i]) + ',' +
                    str(m_index_to_lng[i]) + other_link + '&markers=|' + str(m_index_to_lat[i]) + ',' +
                    str(m_index_to_lng[i]) + '&key=' +
                    api_key, reviews))

    if not top_5:
        sim_w = get_sim_words(q.partition(' ')[0])
        if not sim_w:
            return top_5
        for word in sim_w:
            print(word)
            query = vectorizer.transform([word])
            sim = get_sim(query, 5, doc_by_vocab)[0]
            top_5_idx = np.argsort(sim)[-5:]
            for i in reversed(top_5_idx):
                if (sim[i] > 0 and m_index_to_description[i] != ''):
                    keyword = m_index_to_name[i].split()
                    top_5.append(
                        (m_index_to_name[i], sim[i], m_index_to_description[i],
                         link + 'museum,' + keyword[0],
                         museum_match(m_index_to_name[i]),
                         m_index_to_address[i],
                         map_link + str(m_index_to_lat[i]) + ',' +
                         str(m_index_to_lng[i]) + other_link + '&markers=|' +
                         str(m_index_to_lat[i]) + ',' +
                         str(m_index_to_lng[i]) + '&key=' + api_key))
            if top_5:
                return top_5
    return top_5


def OLD_get_suggestions(q):
    df = pd.read_csv('tripadvisor_merged.csv')
    desc_data = []
    #
    for d in df['Description']:
        if (isinstance(d, float)):
            if (math.isnan(d)):
                desc_data.append('')
        else:
            desc_data.append(d)

    movie_index_to_name = {
        index: movie_name
        for index, movie_name in enumerate(df['MuseumName'])
    }
    movie_index_to_description = {
        index: desc
        for index, desc in enumerate(desc_data)
    }

    vectorizer = build_vectorizer(5000, "english")
    doc_by_vocab = vectorizer.fit_transform(desc_data)
    query = vectorizer.transform([q])
    sim = get_sim(query, 5, doc_by_vocab)[0]
    top_5_idx = np.argsort(sim)[-5:]
    top_5 = []

    for i in reversed(top_5_idx):
        top_5.append(
            (movie_index_to_name[i], sim[i], movie_index_to_description[i]))

    return top_5


def main():
    print(get_suggestions('puppy'))
    #print(museum_match("he"))
    #print(get_sim_words('puppy'))


if __name__ == "__main__":
    main()
