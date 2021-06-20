"""
Course:        DCS 211 Winter 2021 Module D
Assignment:    Final Project
Topic:         Occupation Labor Statistics vs. Gendered Word Similarity

Purpose:       The goal of this project is to scrap the U.S. Bureau of Labor
               Statistics website, specifically using their HTML table for
               the Labor Force Statistics from the Current Population Survey
               data table and compare the percentages of women in occupations
               listed against similar word associated with a known gendered word
               to plot the data in different visualizations.


Student Name: Kendall Williams
Other students outside my pair that I received help from ('N/A' if none):
N/A
Other students outside my pair that I gave help to ('N/A' if none):
N/A

Citations/links of external references used ('N/A' if none):
https://dev.to/coderasha/compare-documents-similarity-using-python-nlp-4odp
https://www.pnas.org/content/115/16/E3635
https://www.pnas.org/content/pnas/suppl/2018/03/30/1720347115.DCSupplemental/pnas.1720347115.sapp.pdf <--Can be used for further Data Manipulation for other Biases outside of Gender
https://stackoverflow.com/
"""
import numpy as np
import pandas as pd
import requests
import json
import time
import re
from time import sleep
from bs4 import BeautifulSoup
import sys
from bs4 import BeautifulSoup
from RPA.Tables import Table
import string
import os
#nltk
import nltk
nltk.download('punkt')
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.corpus import wordnet
from nltk.corpus import words
import gensim, nltk, warnings
warnings.filterwarnings(action='ignore')
#gensim
import gensim
from gensim import models
from gensim.models import Word2Vec
import gensim.downloader as api
from wordcloud import WordCloud
from alive_progress import alive_bar
import matplotlib.pyplot as plt
import seaborn as sns


################################################################################################
def getDataframe(url):
	'''
	Scrapes the U.S. Bureau of Labor Statistics (BLS) website for labor force statistics from the current population
	for HTML table of employed persons by detailed occupation, sex, race, and Hispanic or Latino ethnicity and replicates
	the table into a dataframe of dType = (object,int64, float64).

	Parameters:
	-----------
	url : website
	This url link connects to the U.S. BLS website for labor force statistics from the current
	Population

	Returns:
	--------
	dframe : DataFrame
	This DataFrame is a replica of the HTML table of the BLS website, that replaces null values with zero and includes
	dType = (object,int64, float64(*5)).
	'''

	fname = "occupations.html"
	if os.path.exists(fname):
		# if the local occupations.html already exists, just read its HTML content
		with open(fname, "rb") as infile:
			content = infile.read()
	else:
		# if the local occupations.html  does not exist, fetch via requests.get and
		# then write a local copy of the HTML content to a file
		page = requests.get(url)
		content = page.content
		with open(fname, "wb") as outfile:
			outfile.write(content)

	table_rows = []
	soup = BeautifulSoup(content, "html.parser")
	table = soup.find_all('table', attrs={"class": "regular"})
	#print(table)

	#Remake table from HTML into Dataframe
	table_rows = []
	for table_row in table:
		trs = table_row.find_all('tr')
		ths = table_row.find_all('th')
		cells = table_row.find_all('td')

		# Grab  Occupation data from U.S. Bureau of Labor statistics
		if len(cells) > 0:
			cell_values = []
		if len(ths) > 0:
			occupations = []
			for items in ths:
				occupations.append(items.text.strip())
				#print(occupations)
			occupations = occupations[9::]
			#print(occupations)
			for cell in cells:
				text_ = cell.text.strip()
				#print(text_)
				cell_values.append(text_)
			cell_values = cell_values[:-1]

			# clean array_
			while '' in cell_values:
				cell_values.remove('')  # removes empty spaces in list
			for n, i in enumerate(cell_values):
				if i == '-':  #Replaces - values with None
					cell_values[n] = None
			tot_emp = cell_values[0::6]
			women = cell_values[1::6]
			white = cell_values[2::6]
			black_AF = cell_values[3::6]
			asian_ = cell_values[4::6]
			hispanic_la = cell_values[5::6]

			# Make Pandas DataFrame
			d = {
				'Occupations': occupations,
				'Total Employed': tot_emp,
				'Women': women,
				'White': white,
				'Black or African American': black_AF,
				'Asian': asian_,
				'Hispanic or Latino': hispanic_la
			}
			df = pd.DataFrame(d)
			# Convert each Column in dataframe to numeric
			df = df.replace(',', '', regex=True)
			#print(df)
			c = df.select_dtypes(object).columns.difference([
				'Occupations'
			])  #grabs all colums with data type object except Occupations
			df[c] = df[c].apply(pd.to_numeric, errors='coerce')  #Changes to numeric
			print("***" * 20)
			print(df.shape)
			print(df.dtypes)
			#print(df.describe())
			print("***" * 20)

			#Men Data Missing
			tot_women = (df['Women'] / 100) * df['Total Employed']
			men = df['Total Employed'] - tot_women
			perc_men = round(((men / df['Total Employed']) * 100), 3)

			# Update Dataframe and Excel sheet
			d = {
				'Occupations': occupations,
				'Total Employed': tot_emp,
				'Women': women,
				'Total Employed Women': tot_women,
				'Men': perc_men,
				'White': white,
				'Black or African American': black_AF,
				'Asian': asian_,
				'Hispanic or Latino': hispanic_la
			}
			df = pd.DataFrame(d)
			df = df.replace(',', '', regex=True)
			c = df.select_dtypes(object).columns.difference([
				'Occupations'
			])  #grabs all colums with data type object except Occupations
			df[c] = df[c].apply(pd.to_numeric, errors='coerce')  #Changes to numeric

			#print(df)
			rows, columns = df.shape
			cell_count = rows * columns
			number_of_nulls = df.isnull().sum().sum()
			percentage_of_missing = (number_of_nulls / cell_count) * 100
			print("***" * 20)
			print("Cleaning Dataframe")
			print(f'The number of nulls found: {number_of_nulls}')
			print(f' (Rows,Cols) = ({rows},{columns}) | Cell Count = {cell_count}')
			print(f'Percentage of missing values: {percentage_of_missing}%')
			df = df.fillna(0)
			number_of_nulls = df.isnull().sum().sum()
			percentage_of_missing = (number_of_nulls / cell_count) * 100
			df.to_excel("Labor_Force_2020.xlsx")  # makes the dataframe into excel file
			print(f'The number of nulls found after removal: {number_of_nulls}')
			print(f'Percentage of missing values: {percentage_of_missing}%')
			print("***" * 20)
			#with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
			#print(df)
			print(df.describe())
			print("***" * 20)

	return df


def similarityFunc(corpus):
	"""
	This function takes one parameter corpus and uses one of the word list below to compute the similarity betweeen the
	gendered word and the job from corpus document to be returned in a list.

	Parameters:
	-----------
	corpus : list
	This list corresponds to the occupational words within each job from the U.S. Bureau of Labor Statistics (BLS)
	website for labor force statistics from the current Population

	Returns:
	--------
	list : list
	This list is made up of [job_sims,jobs_List, he_sims, she_sims,difference,], where job_sims is a dictionary, and
	the rest are list that have occupation words used, and similarity values respectfully.
	"""
	word_vectors = api.load(
		"word2vec-google-news-300")  #loads in Google News (about 100 billion words)
	job_sims = {}
	jobs_List = []
	she_sims = []
	he_sims = []
	difference = []
	counter = 0
	woman_words = [
		'she', 'daughter', 'hers', 'her', 'mother', 'woman', 'girl', 'herself',
		'female', 'sister', 'daughters', 'mothers', 'women', 'girls', 'femen',
		'sisters', 'aunt', 'aunts', 'niece', 'nieces'
	]  #list of words that can be used in place of 'she' to test accurancy

	man_words = [
		'he', 'son', 'his', 'him', 'father', 'man', 'boy', 'himself', 'male',
		'brother', 'sons', 'fathers', 'men', 'boys', 'males', 'brothers', 'uncle',
		'uncles', 'nephew', 'nephews'
	]  #list of words that can be used in place of 'he' to test accurancy

	if len(corpus) == 250:
		num = 4 # 4 words are expected not to be in the model
		with alive_bar((len(corpus)) - num) as bar:
			for job in corpus:
				job = str(job.lower())
				if job not in word_vectors:
					print(f" '{job}' not in word vectors")
				else:
					# Check the "most similar words", using the default "cosine similarity" measure. ---> Can also be used to check accurancy
					# Follows the model (King - man + woman = queen)
					most_sim = word_vectors.most_similar(
						positive=['she', job], negative=['he'])
					key, value = most_sim[0]
					#print(f"Similarity of 'she' and {job} = {key},{value}")
					job_sims[key] = value

					similarity_she = word_vectors.similarity('she', job)
					she_sims.append(similarity_she)

					similarity_he = word_vectors.similarity('he', job)
					he_sims.append(similarity_he)
					jobs_List.append(job)
					#print(f"Similarity of 'she' and {job} = {similarity_she}")
					#print(f"Similarity of 'he' and {job} = {similarity_he}")
					if similarity_she > similarity_he:
						diff = similarity_she - similarity_he
					else:
						diff = similarity_he - similarity_she
					difference.append(diff)
					counter += 1
					sleep(0.50)
					bar()
	else:
		num = 7 # 7 words are expected not to be in the model
		with alive_bar((len(corpus)) - num) as bar:
			for job in corpus:
				job = str(job.lower())
				if job not in word_vectors:
					print(f" '{job}' not in word vectors")
				else:
					# Check the "most similar words", using the default "cosine similarity" measure. ---> Can also be used to check accurancy
					# Follows the model (King - man + woman = queen)
					most_sim = word_vectors.most_similar(
						positive=['she', job], negative=['he'])
					key, value = most_sim[0]
					#print(f"Similarity of 'she' and {job} = {key},{value}")
					job_sims[key] = value

					similarity_she = word_vectors.similarity('she', job)
					she_sims.append(similarity_she)

					similarity_he = word_vectors.similarity('he', job)
					he_sims.append(similarity_he)
					jobs_List.append(job)
					#print(f"Similarity of 'she' and {job} = {similarity_she}")
					#print(f"Similarity of 'he' and {job} = {similarity_he}")
					if similarity_she > similarity_he:
						diff = similarity_she - similarity_he
					else:
						diff = similarity_he - similarity_she
					difference.append(diff)
					counter += 1
					sleep(0.50)
					bar()
	return [
		job_sims,
		jobs_List,
		he_sims,
		she_sims,
		difference,
	]


# Plot Data
def model(sims, df):
	"""
	This function takes two parameters sims and df and uses the information in both to plot different Visualizations of
	similarity and occupational data.

	Parameters:
	-----------
	sims : list
	This list is made up of [job_sims,jobs_List, he_sims, she_sims,difference,], where job_sims is a dictionary, and
	the rest are list that have occupation words used, and similarity values respectfully.
	df   :  DataFrame
	This DataFrame is a replica of the HTML table of the BLS website, that replaces null values with zero and includes
	dType = (object,int64, float64(*5)).

	Returns:
	--------
	Plot Visualizations using matplotlib, WordCloud, and seaborn libraries

	"""
	jobs_dictMostSim = sims[0]
	jobs_List = sims[1]
	man_sims = sims[2]
	woman_sims = sims[3]
	diff_vals = sims[4]
	jobs_df = pd.DataFrame(
		list(jobs_dictMostSim.items()), columns=['Key', 'value'])
	df2 = pd.DataFrame({
		'Job_Words': jobs_List,
		'Woman_Similarity_of_Job': woman_sims,
		'Man_Similarity_of_Job': man_sims,
		'Difference': diff_vals
	})
	print(df2.describe)

	# Creating Word Cloud for Occupations
	textfile = open("jobs_file.txt", "w")
	for element in df['Occupations']:
		textfile.write(element + "\n")
	textfile.close()
	file = open('jobs_file.txt', 'r')
	raw_text = file.read()
	text = raw_text.replace("\n", " ")

	data = []
	for i in sent_tokenize(text):
		temp = []
	for j in word_tokenize(i):
		temp.append(j.lower())
	data.append(temp)

	# Word Cloud
	jobs_wc = WordCloud(
		background_color='white', width=600, height=512).generate(text)
	plt.figure(figsize=(12, 8), facecolor='k')
	plt.imshow(jobs_wc)

	#plot of Dataframe data showing Women percentages in Occupations

	# Draw a bar graph with the number of women working in each occupation at each bar
	#BEWARE The print out of this bar graph is very hard to read
	#To see better comparisons of percentages in jobs refer to excel sheet of Labor_Force_2020 data.
	x = df['Men']
	y = df['Women']

	fig, ax = plt.subplots()
	width = 0.75  # the width of the bars
	ind = np.arange(len(y))  # the x locations for the groups
	ax.barh(ind, y, width, color="blue")
	ax.set_yticks(ind + width / 2)
	ax.set_yticklabels(x, minor=False)
	plt.title('Percent of Men & Women in Occupations')
	plt.xlabel('x')
	plt.ylabel('y')
	plt.savefig(
		os.path.join('Percent of Men & Women in Occupations.png'),
		dpi=300,
		format='png',
		bbox_inches='tight')

	#Histograms of Gendered word compared to occupation and difference between the two
	sns.jointplot(
		df2['Difference'], df2['Man_Similarity_of_Job'], kind='hist', color='orange')
	plt.title("Man Word Similarity & Difference ")
	plt.savefig(
		os.path.join('Histogram of Diff Man Similarity.png'),
		dpi=300,
		format='png',
		bbox_inches='tight')

	sns.jointplot(
		df2['Difference'], df2['Woman_Similarity_of_Job'], kind='hist', color='blue')
	plt.title("Woman Word Similarity & Difference ")
	plt.savefig(
		os.path.join('Histogram of Diff Woman Similarity.png'),
		dpi=300,
		format='png',
		bbox_inches='tight')

	#Plots Scatter plot and words close to similarity values
	plt.figure(figsize=(10, 10))
	p1 = sns.scatterplot(
		'Difference',  # Horizontal axis
		'Man_Similarity_of_Job',  # Vertical axis
		data=df2,  # Data source
		size=8,
		legend=False,
		color=['red', 'orange'])

	for line in range(0, df2.shape[0]):
		p1.text(
			df2.Difference[line] + 0.01,
			df2.Man_Similarity_of_Job[line],
			df2.Job_Words[line],
			horizontalalignment='left',
			size='medium',
			color='black',
			weight='semibold')

	plt.title('Occupation Labor Statistics vs. Man Word Similarity')
	# Set x-axis label
	plt.xlabel('Difference b/w Gender and Word Similarity')
	# Set y-axis label
	plt.ylabel('Man Similarity and Job')
	plt.savefig(
		os.path.join('Occupation Labor Statistics vs. Man Word Similarity.png'),
		dpi=300,
		format='png',
		bbox_inches='tight')

	plt.figure(figsize=(10, 10))
	p2 = sns.scatterplot(
		'Difference',  # Horizontal axis
		'Woman_Similarity_of_Job',  # Vertical axis
		data=df2,  # Data source
		size=8,
		legend=False,
		color=['red', 'blue'])

	for line in range(0, df2.shape[0]):
		p2.text(
			df2.Difference[line] + 0.01,
			df2.Woman_Similarity_of_Job[line],
			df2.Job_Words[line],
			horizontalalignment='left',
			size='medium',
			color='black',
			weight='semibold')

	plt.title('Occupation Labor Statistics vs. Gendered Word Similarity')
	# Set x-axis label
	plt.xlabel('Difference b/w Gender and Word Similarity')
	# Set y-axis label
	plt.ylabel('Woman Similarity and Job')
	plt.savefig(
		os.path.join('Occupation Labor Statistics vs. Woman Word Similarity.png'),
		dpi=300,
		format='png',
		bbox_inches='tight')
	plt.show()

	plt.figure(figsize=(20, 10))
	p3 = sns.scatterplot(
		'Man_Similarity_of_Job',  # Horizontal axis
		'Woman_Similarity_of_Job',  # Vertical axis
		data=df2,  # Data source
		size=8,
		legend=False,
		color=['orange', 'blue'])

	for line in range(0, df2.shape[0]):
		p2.text(
			df2.Man_Similarity_of_Job[line] + 0.01,
			df2.Woman_Similarity_of_Job[line],
			df2.Job_Words[line],
			horizontalalignment='left',
			size='medium',
			color='black',
			weight='semibold')

	plt.title('Woman Similarity vs. Man Similarity')
	# Set x-axis label
	plt.xlabel('Man_Similarity_of_Job')
	# Set y-axis label
	plt.ylabel('Woman_Similarity_of_Job')
	plt.savefig(
		os.path.join('Woman Similarity vs. Man Similarity.png'),
		dpi=300,
		format='png',
		bbox_inches='tight')
	plt.show()


def main():

	url = "https://www.bls.gov/cps/cpsaat11.htm"  #Labor_Force_2020
	################## GET DATAFRAME ###################################################################################333
	dataframe = getDataframe(url)  #retruns dataframe
	time.sleep(3)

	################## BUILD CORPUS ######################################################################################3
	# Splits the data set into two corpus documents
	data = dataframe.to_numpy()  #changes dataframe to numpy array
	corpus_1 = data[0:int(0.8 * len(data))]
	time.sleep(3)
	corpus_2 = data[int(0.8 * len(data)):]

	################## CORPUS DOC 1 #######################################################################################3
	time.sleep(3)
	np.set_printoptions(threshold=sys.maxsize)
	counter = 1
	for i in range(8):
		corpus_1 = np.delete(
			corpus_1, counter,
			axis=1)  #gets rid of numeric data ; corpus_1 is now only occpations
	corpus_1 = corpus_1.astype('U')
	corpus_1 = np.char.lower(corpus_1)

	stop_words = set(stopwords.words('english'))
	i = 0
	corpus1 = []
	print("***" * 20)
	print("Building Corpus Data from first 80 % of data set "
							)  # expected = 476 for 476/595
	with alive_bar(476) as bar:
		print("Processing Corpus Doc 1:")
		while i != len(corpus_1):
			for jobs in corpus_1:
				for word in jobs:
					corpus_1_tokens = word_tokenize(word)
					corpus_1_tokens = [
						word for word in corpus_1_tokens if not word in stopwords.words()
					]
					corpus1.append(corpus_1_tokens)
					i += 1
					sleep(0.03)
					bar()
	#further cleaning
	corpus1 = corpus1[1:]
	print(f'Total Occupations from Dataframe: {len(corpus1)}')  #expected = 476
	print('Occupations data will be split into separate words for better fitting')
	corpus1 = [' '.join(i) for i in corpus1]
	corpus1 = [i for item in corpus1 for i in item.split()]
	print(f'Total words from Occupations before cleaning:{len(corpus1)}')
	corpus1 = [
		''.join(c for c in s if c not in string.punctuation) for s in corpus1
	]
	corpus1 = [s for s in corpus1 if s]
	corpus1 = sorted(set(corpus1), key=lambda x: corpus1.index(x))
	print(f'Total words from Occupations after cleaning:{len(corpus1)}')
	print(f'Corpus: {corpus1[:10]}...')
	print("***" * 20)

	############################## CORPUS  DOC 2 #############################################################################
	time.sleep(3)
	np.set_printoptions(threshold=sys.maxsize)
	counter = 1
	for i in range(8):
		corpus_2 = np.delete(
			corpus_2, counter,
			axis=1)  #gets rid of numeric data ; corpus_2 is now only occpations
	corpus_2 = corpus_2.astype('U')
	corpus_2 = np.char.lower(corpus_2)

	stop_words = set(stopwords.words('english'))
	i = 0
	corpus2 = []
	print("***" * 20)
	print("Building Corpus Features Data from last 20 % of data set "
							)  # expected = 119 for 119/595
	with alive_bar(119) as bar:
		print("Processing Corpus features:")
		while i != len(corpus_2):
			for jobs in corpus_2:
				for word in jobs:
					corpus_2_tokens = word_tokenize(word)
					corpus_2_tokens = [
						word for word in corpus_2_tokens if not word in stopwords.words()
					]
					corpus2.append(corpus_2_tokens)
					i += 1
					sleep(0.03)
					bar()
	#further cleaning
	print(f'Total Occupations from Dataframe: {len(corpus2)}')  #expected = 119
	print('Occupations data will be split into separate words for better fitting')
	corpus2 = [' '.join(i) for i in corpus2]
	corpus2 = [i for item in corpus2 for i in item.split()]
	print(f'Total words from Occupations before cleaning:{len(corpus2)}')
	corpus2 = [
		''.join(c for c in s if c not in string.punctuation) for s in corpus2
	]
	corpus2 = [s for s in corpus2 if s]
	corpus2 = sorted(set(corpus2), key=lambda x: corpus2.index(x))
	print(f'Total words from Occupations after cleaning:{len(corpus2)}')
	print(f'Corpus: {corpus2[:10]}...')
	print("***" * 20)
	time.sleep(3)

	################## BUILD SIMILARITY FUNCTION ######################################################################################
	print("***" * 20)
	print("Preparing to Build Data for Model.")
	similarity = similarityFunc(corpus2)
	#similarity = similarityFunc(corpus1) # To change between models use; Corpus 1 is longer
	print("***" * 20)
	time.sleep(3)
	model(similarity, dataframe)


if __name__ == "__main__":
	main()
