# Chatbot de Gestion Hôtelière

## Description

Ce projet consiste en la création d'un **chatbot spécialisé pour la gestion hôtelière**. Conçu pour répondre aux besoins des hôtels et améliorer l'expérience client, ce chatbot peut gérer diverses requêtes telles que les réservations de chambres, les informations sur les services, les annulations, et plus encore. Utilisant des techniques de traitement du langage naturel (NLP), il est capable de comprendre et répondre de manière naturelle aux questions des utilisateurs.

## Fonctionnalités

- **Réservation de chambres** : Permet aux utilisateurs de réserver des chambres en fonction de la disponibilité et du type de chambre souhaité.

- **Annulation et Prolongation de réservation** : Permet aux utilisateurs d'annuler ou de prolonger leurs réservations existantes.

- **Informations sur les services** : Fournit des informations sur les services de l'hôtel tels que la piscine, le restaurant, le spa, etc.

- **Gestion des sessions** : Garde le contexte de la conversation pour fournir des réponses pertinentes et contextuelles.

- **Amélioration continue** : Enregistre les questions inconnues pour améliorer le modèle et utilise l'apprentissage par renforcement pour optimiser les réponses du chatbot.

## Technologies Utilisées

- **Python** : Langage principal utilisé pour le développement.

- **PyTorch** : Utilisé pour la création et l'entraînement du modèle de machine learning.

- **NLTK (Natural Language Toolkit)** : Utilisé pour le traitement du langage naturel.

- **MySQL** : Base de données utilisée pour stocker les informations des utilisateurs, des réservations, des clients, etc.

- **Gym (OpenAI)** : Utilisé pour l'environnement d'apprentissage par renforcement.

## Structure du Projet

- `chatbot_env.py` : Définition de l'environnement pour l'apprentissage par renforcement.

- `train_rl.py` : Entraînement de l'agent d'apprentissage par renforcement.

- `model.py` : Définition du modèle de réseau de neurones pour la compréhension du langage.

- `chat.py` : Script principal gérant l'interaction avec l'utilisateur et les requêtes à la base de données.

- `intents.json` : Fichier JSON contenant les données d'entraînement pour les intents et les patterns.

- `data.pth` : Fichier contenant le modèle de réseau de neurones pré-entraîné.

- `requirements.txt` : Liste des bibliothèques Python nécessaires au projet.

## Prérequis

Avant de commencer, assurez-vous d'avoir installé les éléments suivants :

- Python 3.7 ou supérieur

- MySQL Server

- Environnement virtuel Python (`virtualenv` ou `venv`)

## Installation

1\. **Clonez le dépôt du projet** :

    
    git clone https://github.com/Silanoa/hotel-chatbot.git
    cd chatbot-hotel-management
    


2\. **Créez et activez un environnement virtuel** :

    
    python -m venv venv
    source venv/bin/activate  # Sur Windows utilisez `venv\Scripts\activate`
    

3\. **Installez les dépendances** :

    
    pip install -r requirements.txt
    

4\. **Configurez la base de données MySQL** :

   - Créez une base de données MySQL nommée `hotel_chatbot`.

   - Importez les schémas de tables nécessaires (`user_sessions`, `reservations`, `clients`, `chambres`, etc.) à partir du fichier `database_schema.sql`.

5\. **Définissez les variables d'environnement** :

   Créez un fichier `.env` à la racine du projet et ajoutez les informations de connexion à votre base de données MySQL :

    
    DB_USER=root
    DB_PASSWORD=yourpassword
    DB_HOST=localhost
    DB_NAME=hotel_chatbot
    

## Utilisation

1\. **Lancez le chatbot** :

  
    python chat.py
    DB_USER=root
    

2\. **Interagissez avec le chatbot** :

   Le chatbot démarrera et vous pourrez commencer à poser des questions sur les services de l'hôtel, effectuer des réservations, annuler des réservations, etc.

## Amélioration Continue

Le chatbot est conçu pour s'améliorer au fil du temps grâce à deux mécanismes principaux :

1\. **Enregistrement des Questions Inconnues** : Les questions que le chatbot ne peut pas comprendre sont enregistrées dans la base de données `questions_inconnues` pour analyse ultérieure et réentraînement.

2\. **Apprentissage par Renforcement** : Utilisation de l'apprentissage par renforcement via `chatbot_env.py` et `train_rl.py` pour ajuster les réponses du chatbot en fonction des interactions des utilisateurs.

Pour réentraîner le modèle avec de nouvelles données ou en fonction des questions inconnues :

    
    python train.py  # Pour réentraîner le modèle de NLP
    
    python train_rl.py  # Pour l'apprentissage par renforcement
    
