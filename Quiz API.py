import pandas as pd
import random
import os
from kaggle.api.kaggle_api_extended import KaggleApi
import zipfile

# Configuro l'API di Kaggle
api = KaggleApi()
api.authenticate()

# Percorso del dataset su Kaggle
dataset_path = 'ashirwadsangwan/imdb-dataset'
local_path = 'datasets/imdb'

# Creo la cartella se non esiste già
os.makedirs(local_path, exist_ok=True)

# Scarico i dataset
files = ['name.basics.tsv', 'title.akas.tsv', 'title.basics.tsv', 'title.principals.tsv', 'title.ratings.tsv']

for file in files:
    api.dataset_download_file(dataset_path, file_name=file, path=local_path)
    with zipfile.ZipFile(f"{local_path}/{file}.zip", 'r') as zip_ref:
        zip_ref.extractall(local_path)

path = local_path

# Carico solo le colonne necessarie dai file TSV
name_basics = pd.read_csv(f'{path}/name.basics.tsv', sep='\t', usecols=['nconst', 'primaryName'], dtype=str, low_memory=False)
title_basics = pd.read_csv(f'{path}/title.basics.tsv', sep='\t', usecols=['tconst', 'primaryTitle', 'startYear', 'titleType'], dtype=str, low_memory=False)
title_principals = pd.read_csv(f'{path}/title.principals.tsv', sep='\t', usecols=['tconst', 'nconst', 'category'], dtype=str, low_memory=False)
title_ratings = pd.read_csv(f'{path}/title.ratings.tsv', sep='\t', usecols=['tconst', 'averageRating', 'numVotes'], dtype=str, low_memory=False)

# Filtro solo i film e attori principali
movies = title_basics[title_basics['titleType'] == 'movie']
actors_principals = title_principals[(title_principals['category'] == 'actor') | (title_principals['category'] == 'actress')]

# Unisco i dati dei film con i dati degli attori principali e delle valutazioni
movies = movies.merge(actors_principals, on='tconst')
movies = movies.merge(title_ratings, on='tconst')

# Decido arbitrariamente di prendere in considerazione solo i film un pelo più popolari e con valutazioni superiori alla media (il voto medio dei film si aggira comunque intorno al 6)
movies = movies[(pd.to_numeric(movies['numVotes'], errors='coerce').fillna(0) >= 1000) & 
                (pd.to_numeric(movies['averageRating'], errors='coerce').fillna(0) >= 6)]

# Genero le domande
def generate_question(movie):
    principal_cast = movie['nconst']
    if pd.notna(principal_cast):
        correct_answer = principal_cast
        question = f"Chi ha recitato nel film '{movie['primaryTitle']}' ({movie['startYear']})?"

        all_actors = actors_principals['nconst'].dropna().unique().tolist()
        wrong_answers = random.sample([a for a in all_actors if a != correct_answer], 3)
        wrong_answers_names = name_basics[name_basics['nconst'].isin(wrong_answers)]['primaryName'].tolist()
        correct_answer_name = name_basics[name_basics['nconst'] == correct_answer]['primaryName'].values[0]
        options = wrong_answers_names + [correct_answer_name]
        random.shuffle(options)
        return question, options, correct_answer_name
    else:
        return None, None, None

# Permetto al giocatore di rispondere solo con risposte valide (numeri tra 1 a 4)
def ask_question(question, options):
    if question and options:
        print(question)
        for i, option in enumerate(options):
            print(f"{i+1}. {option}")
        while True:
            try:
                answer = int(input("La tua risposta (1-4): ").strip())
                if 0 < answer <= 4:
                    return options[answer - 1]
                else:
                    print("Per favore, inserisci un numero tra 1 e 4.")
            except ValueError:
                print("Per favore, inserisci un numero valido.")

# Calcolo del punteggio
def calculate_score(correct, difficulty):
    return 10 * difficulty if correct else 0

# Chiedo quante domande vuole il giocatore ed il livello di difficoltà (come criterio di scelta per la difficoltà ho deciso di considerare quanto recenti siano i film)
def main():
    while True:
        try:
            num_questions = int(input("Quante domande vuoi (1-10)? ").strip())
            if 1 <= num_questions <= 10:
                break
            else:
                print("Per favore, inserisci un numero tra 1 e 10.")
        except ValueError:
            print("Per favore, inserisci un numero valido.")
    
    while True:
        try:
            difficulty = int(input("Scegli la difficoltà (1-3): ").strip())
            if 1 <= difficulty <= 3:
                break
            else:
                print("Per favore, inserisci un numero tra 1 e 3.")
        except ValueError:
            print("Per favore, inserisci un numero valido.")

    score = 0
    questions_asked = 0

    for _ in range(num_questions):
        filtered_movies = movies
        current_year = pd.Timestamp.now().year

        if difficulty == 1:
            filtered_movies = filtered_movies[pd.to_numeric(filtered_movies['startYear'], errors='coerce').fillna(0) >= current_year - 10]
        elif difficulty == 2:
            filtered_movies = filtered_movies[pd.to_numeric(filtered_movies['startYear'], errors='coerce').fillna(0) >= current_year - 20]

        if filtered_movies.empty:
            print("NESSUNA DOMANDA FORMULABILE")
            break

        movie = filtered_movies.sample().iloc[0]
        question, options, correct_answer = generate_question(movie)
        if question and options:
            user_answer = ask_question(question, options)
            if user_answer == correct_answer:
                score += calculate_score(True, difficulty)
                print("Risposta corretta!")
            else:
                print(f"Risposta sbagliata. La risposta corretta era: {correct_answer}")
            print()
            questions_asked += 1
        else:
            print("Impossibile generare una domanda per questo film. Passo al prossimo.")

    if questions_asked > 0:
        print(f"Il tuo punteggio finale è: {score}. Grazie per aver giocato!")
    else:
        print("Nessuna domanda formulabile.")

if __name__ == "__main__":
    main()
