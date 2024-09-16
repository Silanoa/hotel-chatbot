import random
import json
import torch
import torch.nn.functional as F
import mysql.connector
import logging
import os
from datetime import datetime, timedelta
import re

from model import NeuralNet
from nltk_utils import bag_of_words, tokenize, stem, stop_words

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Charger les variables d'environnement pour la sécurité
from dotenv import load_dotenv
load_dotenv()

# Connexion à la base de données MySQL
db_config = {
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'rosalex2000'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'hotel_chatbot')
}

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    logging.info("Connexion à la base de données réussie.")
except mysql.connector.Error as err:
    logging.error(f"Erreur de connexion à la base de données : {err}")
    exit(1)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Charger les intentions
with open('intents.json', 'r', encoding='utf-8') as json_data:
    intents = json.load(json_data)

# Charger le modèle entraîné
FILE = "data.pth"
try:
    data = torch.load(FILE, map_location=device)
    logging.info("Modèle chargé avec succès.")
except FileNotFoundError:
    logging.error(f"Fichier {FILE} non trouvé.")
    exit(1)
except Exception as e:
    logging.error(f"Erreur lors du chargement du modèle : {e}")
    exit(1)

input_size = data.get("input_size")
hidden_size = data.get("hidden_size")
output_size = data.get("output_size")
all_words = data.get('all_words', [])
tags = data.get('tags', [])
model_state = data.get("model_state")

if not all_words or not tags or not model_state:
    logging.error("Les données du modèle sont incomplètes.")
    exit(1)

# Charger le modèle de réseau de neurones
model = NeuralNet(input_size, hidden_size, output_size).to(device)
model.load_state_dict(model_state)
model.eval()

bot_name = "Assistant"

# Définir le timeout des sessions (en minutes)
SESSION_TIMEOUT = 30

# Définir les états possibles
STATE = {
    'NONE': 'none',
    'RESERVATION': 'reservation',
    'CANCEL': 'cancel',
    'EXTEND': 'extend',
    'FEEDBACK': 'feedback'
}

def get_user_session(user_id):
    try:
        cursor.execute("SELECT session_data, last_active FROM user_sessions WHERE user_id=%s", (user_id,))
        result = cursor.fetchone()
        if result:
            session_data = json.loads(result['session_data'])
            last_active = result['last_active']
            if datetime.now() - last_active > timedelta(minutes=SESSION_TIMEOUT):
                session_data = {'state': STATE['NONE'], 'history': []}
                cursor.execute("UPDATE user_sessions SET session_data=%s, last_active=NOW() WHERE user_id=%s",
                               (json.dumps(session_data), user_id))
                conn.commit()
                logging.info(f"Session pour user_id {user_id} réinitialisée en raison d'inactivité.")
        else:
            session_data = {'state': STATE['NONE'], 'history': []}
            cursor.execute("INSERT INTO user_sessions (user_id, session_data, last_active) VALUES (%s, %s, NOW())",
                           (user_id, json.dumps(session_data)))
            conn.commit()
        
        if 'history' not in session_data:
            session_data['history'] = []
        
        return session_data
    except mysql.connector.Error as err:
        logging.error(f"Erreur lors de la récupération de la session utilisateur : {err}")
        return {'state': STATE['NONE'], 'history': []}

def save_user_session(user_id, session_data):
    try:
        cursor.execute("UPDATE user_sessions SET session_data=%s, last_active=NOW() WHERE user_id=%s",
                       (json.dumps(session_data), user_id))
        conn.commit()
    except mysql.connector.Error as err:
        logging.error(f"Erreur lors de la sauvegarde de la session utilisateur : {err}")

def get_responses(tag):
    for intent in intents['intents']:
        if intent["tag"] == tag:
            return intent['responses']
    return []

def save_unknown_question(question):
    try:
        cursor.execute("INSERT INTO questions_inconnues (question_text, date_recue) VALUES (%s, %s)",
                       (question, datetime.now()))
        conn.commit()
        logging.info(f"Question inconnue enregistrée: {question}")
    except mysql.connector.Error as err:
        logging.error(f"Erreur lors de l'enregistrement de la question inconnue : {err}")

def save_feedback(user_id, question_text, bot_response, user_feedback):
    try:
        cursor.execute(
            "INSERT INTO feedbacks (question_text, bot_response, user_feedback, user_id, date_recue) VALUES (%s, %s, %s, %s, %s)",
            (question_text, bot_response, user_feedback, user_id, datetime.now()))
        conn.commit()
        logging.info(f"Feedback enregistré pour user_id {user_id}: {user_feedback}")
    except mysql.connector.Error as err:
        logging.error(f"Erreur lors de l'enregistrement du feedback : {err}")

def validate_date(date_text):
    try:
        return datetime.strptime(date_text, '%d/%m/%Y')
    except ValueError:
        return None

def convert_date_format(date_obj):
    return date_obj.strftime('%Y-%m-%d')

def check_room_availability(type_chambre, date_checkin, date_checkout):
    try:
        checkin = date_checkin.date()
        checkout = date_checkout.date()
        cursor.execute("""
            SELECT COUNT(*) as booked FROM reservations 
            WHERE chambre_id IN (
                SELECT chambre_id FROM chambres WHERE type_chambre=%s
            ) AND (
                (date_checkin <= %s AND date_checkout > %s) OR
                (date_checkin < %s AND date_checkout >= %s) OR
                (date_checkin >= %s AND date_checkout <= %s)
            )
        """, (type_chambre, checkin, checkin, checkout, checkout, checkin, checkout))
        booked = cursor.fetchone()['booked']
        cursor.execute("SELECT COUNT(*) as total FROM chambres WHERE type_chambre=%s", (type_chambre,))
        total = cursor.fetchone()['total']
        return booked < total
    except mysql.connector.Error as err:
        logging.error(f"Erreur lors de la vérification de la disponibilité des chambres : {err}")
        return False

def check_reservation_exists(reservation_id):
    """Vérifie si une réservation existe dans la base de données."""
    try:
        cursor.execute("SELECT * FROM reservations WHERE reservation_id=%s", (reservation_id,))
        return cursor.fetchone() is not None
    except mysql.connector.Error as err:
        logging.error(f"Erreur lors de la vérification de la réservation : {err}")
        return False

def get_reservation_info(reservation_id):
    """Récupère les informations sur une réservation existante."""
    try:
        cursor.execute("""
            SELECT r.reservation_id, r.date_checkin, r.date_checkout, c.type_chambre, cl.nom, cl.prenom
            FROM reservations r
            JOIN chambres c ON r.chambre_id = c.chambre_id
            JOIN clients cl ON r.client_id = cl.client_id
            WHERE r.reservation_id=%s
        """, (reservation_id,))
        return cursor.fetchone()
    except mysql.connector.Error as err:
        logging.error(f"Erreur lors de la récupération des informations de la réservation : {err}")
        return None

def reset_session_data(session_data):
    session_data['state'] = STATE['NONE']
    session_data['history'] = []
    keys_to_remove = ['intent', 'step', 'type_chambre', 'date_checkin', 'date_checkout',
                      'name', 'reservation_id', 'last_question', 'last_bot_response']
    for key in keys_to_remove:
        session_data.pop(key, None)
    return session_data

def handle_room_booking(user_id, session_data):
    name = session_data.get('name', 'Client')
    type_chambre = session_data.get('type_chambre', 'Double')
    date_checkin_str = session_data.get('date_checkin', '')
    date_checkout_str = session_data.get('date_checkout', '')

    date_checkin = validate_date(date_checkin_str)
    date_checkout = validate_date(date_checkout_str)

    if not date_checkin or not date_checkout:
        session_data = reset_session_data(session_data)
        save_user_session(user_id, session_data)
        return "Format de date invalide. Veuillez entrer la date au format JJ/MM/AAAA."

    date_checkin_mysql = convert_date_format(date_checkin)
    date_checkout_mysql = convert_date_format(date_checkout)

    if not check_room_availability(type_chambre, date_checkin, date_checkout):
        logging.info(f"Aucune chambre disponible de type {type_chambre} pour les dates {date_checkin_mysql} - {date_checkout_mysql}.")
        session_data = reset_session_data(session_data)
        save_user_session(user_id, session_data)
        return "Désolé, aucune chambre de ce type n'est disponible pour les dates choisies."

    try:
        cursor.execute("SELECT chambre_id, prix FROM chambres WHERE type_chambre=%s AND est_disponible=1 LIMIT 1", (type_chambre,))
        chambre = cursor.fetchone()
        if chambre:
            chambre_id, prix = chambre['chambre_id'], chambre['prix']
            cursor.execute("SELECT COUNT(*) as total_reservations FROM reservations")
            total_reservations = cursor.fetchone()['total_reservations']
            reservation_id = f"RES{total_reservations+1:05d}"
            nom_prenom = name.split()
            nom = nom_prenom[0]
            prenom = nom_prenom[1] if len(nom_prenom) > 1 else ''
            cursor.execute("INSERT INTO clients (nom, prenom) VALUES (%s, %s)", (nom, prenom))
            client_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO reservations (reservation_id, client_id, chambre_id, date_checkin, date_checkout) VALUES (%s, %s, %s, %s, %s)",
                (reservation_id, client_id, chambre_id, date_checkin_mysql, date_checkout_mysql)
            )
            conn.commit()
            cursor.execute("UPDATE chambres SET est_disponible=0 WHERE chambre_id=%s", (chambre_id,))
            conn.commit()
            response_template = random.choice(get_responses('confirmation_reservation'))
            response = response_template.format(name=name, reservation_id=reservation_id)
            logging.info(f"Réservation effectuée pour {name}, ID réservation : {reservation_id}")
            recap = (f"Récapitulatif de votre réservation:\n"
                     f"Nom: {name}\n"
                     f"Type de chambre: {type_chambre}\n"
                     f"Dates: {date_checkin_str} au {date_checkout_str}\n"
                     f"Numéro de réservation: {reservation_id}")
            session_data['history'].append({'bot': response})
            session_data['history'].append({'bot': recap})
            session_data = reset_session_data(session_data)
            save_user_session(user_id, session_data)
            return f"{response}\n\n{recap}\n\n{random.choice(get_responses('reprise_apres_action'))}"
        else:
            logging.info(f"Aucune chambre disponible de type {type_chambre}.")
            session_data = reset_session_data(session_data)
            save_user_session(user_id, session_data)
            return "Désolé, aucune chambre de ce type n'est disponible pour le moment."
    except mysql.connector.Error as err:
        logging.error(f"Erreur lors de la réservation de la chambre : {err}")
        session_data = reset_session_data(session_data)
        save_user_session(user_id, session_data)
        return "Désolé, une erreur est survenue lors de la réservation. Veuillez réessayer plus tard."

def handle_intent(tag, msg, user_id, session_data):
    if session_data['state'] == STATE['NONE']:
        # Gérer les intents quand il n'y a pas de processus en cours
        if tag in ["salutation_matin", "salutation_soir"]:
            return random.choice(get_responses(tag))
        
        elif tag == "au_revoir":
            return random.choice(get_responses(tag))
        
        elif tag == "reset":
            session_data = reset_session_data(session_data)
            save_user_session(user_id, session_data)
            return random.choice(get_responses(tag))
        
        elif tag == "feedback":
            session_data['state'] = STATE['FEEDBACK']
            session_data['step'] = 'feedback_rating'
            save_user_session(user_id, session_data)
            return random.choice(get_responses(tag))
        
        elif tag == "reservation_chambre":
            session_data['state'] = STATE['RESERVATION']
            session_data['step'] = 'demande_type_chambre'
            save_user_session(user_id, session_data)
            return random.choice(get_responses(tag))
        
        elif tag == "ask_reservation_possibility":
            return random.choice(get_responses(tag))
        
        elif tag == "confirm_reservation":
            # Activer le processus de réservation après confirmation de l'utilisateur
            session_data['state'] = STATE['RESERVATION']
            session_data['step'] = 'demande_type_chambre'
            save_user_session(user_id, session_data)
            return random.choice(get_responses('confirm_reservation'))
        
        elif tag == "annuler_reservation":
            session_data['state'] = STATE['CANCEL']
            session_data['step'] = 'demande_numero_reservation'
            save_user_session(user_id, session_data)
            return random.choice(get_responses(tag))
        
        elif tag == "prolonger_sejour":
            session_data['state'] = STATE['EXTEND']
            session_data['step'] = 'demande_numero_reservation_extend'
            save_user_session(user_id, session_data)
            return "Veuillez fournir votre numéro de réservation pour prolonger (ex: RES00001)."
        
        elif tag == "annuler_action" and session_data['last_bot_response'] and "réservations" in session_data['last_bot_response'].lower():
            # Annuler l'action uniquement si le dernier bot a parlé d'une action (comme une réservation)
            session_data = reset_session_data(session_data)
            save_user_session(user_id, session_data)
            return random.choice(get_responses(tag))
        
        elif tag in [
            'service_piscine', 'service_spa', 'service_restaurant',
            'service_salle_de_sport', 'service_parking', 'service_wifi',
            'faq_horaires_restaurant', 'faq_disponibilite_services',
            'faq_tarifs_chambres', 'faq_modalites_paiement',
            'renseignements_generaux', 'assistance_technique'
        ]:
            return random.choice(get_responses(tag))
        
        else:
            return random.choice(get_responses('indefini')) + "\n\n" + random.choice(get_responses('reprise_apres_action'))
    # Gestion des états spécifiques
    elif session_data['state'] == STATE['RESERVATION']:
        return handle_reservation_intent(tag, msg, user_id, session_data)
    
    elif session_data['state'] == STATE['CANCEL']:
        return handle_cancel_intent(tag, msg, user_id, session_data)
    
    elif session_data['state'] == STATE['EXTEND']:
        return handle_extend_intent(tag, msg, user_id, session_data)
    
    elif session_data['state'] == STATE['FEEDBACK']:
        return handle_feedback_intent(tag, msg, user_id, session_data)
    
    else:
        session_data = reset_session_data(session_data)
        save_user_session(user_id, session_data)
        return random.choice(get_responses('indefini')) + "\n\n" + random.choice(get_responses('reprise_apres_action'))

def handle_reservation_intent(tag, msg, user_id, session_data):
    step = session_data.get('step', 'none')
    
    # Vérifier si l'utilisateur veut annuler l'action actuelle à tout moment
    if tag == 'annuler_action':
        session_data = reset_session_data(session_data)
        save_user_session(user_id, session_data)
        return "Action annulée. Comment puis-je vous aider autrement?"

    # Continuer avec les étapes de la réservation
    if session_data.get('last_question') == msg:
        return "Vous avez déjà mentionné cela. Pouvez-vous fournir des informations différentes ?"
    
    if step == 'demande_type_chambre':
        valid_types = ['simple', 'double', 'suite']
        if msg.lower() in valid_types:
            session_data['type_chambre'] = msg.capitalize()
            session_data['step'] = 'demande_dates_checkin'
            save_user_session(user_id, session_data)
            return "Quelle est la date de check-in? (format JJ/MM/AAAA)"
        else:
            return "Type de chambre invalide. Veuillez choisir entre simple, double ou suite."
    
    elif step == 'demande_dates_checkin':
        date_checkin = validate_date(msg)
        if date_checkin:
            session_data['date_checkin'] = msg
            session_data['step'] = 'demande_dates_checkout'
            save_user_session(user_id, session_data)
            return "Quelle est la date de check-out? (format JJ/MM/AAAA)"
        else:
            return "Format de date invalide. Veuillez entrer la date au format JJ/MM/AAAA."
    
    elif step == 'demande_dates_checkout':
        date_checkout = validate_date(msg)
        if date_checkout:
            checkin = validate_date(session_data['date_checkin'])
            if date_checkout > checkin:
                session_data['date_checkout'] = msg
                session_data['step'] = 'demande_nom'
                save_user_session(user_id, session_data)
                return "Pouvez-vous me donner votre nom, s'il vous plaît?"
            else:
                return "La date de check-out doit être après la date de check-in. Veuillez entrer une date valide."
        else:
            return "Format de date invalide. Veuillez entrer la date au format JJ/MM/AAAA."
    
    elif step == 'demande_nom':
        session_data['name'] = msg
        response = handle_room_booking(user_id, session_data)
        return response
    
    else:
        session_data = reset_session_data(session_data)
        save_user_session(user_id, session_data)
        return "Désolé, une erreur est survenue. La session a été réinitialisée. Veuillez réessayer."

def handle_cancel_intent(tag, msg, user_id, session_data):
    step = session_data.get('step', 'none')
    
    if step == 'demande_numero_reservation':
        if re.match(r'^RES\d{5}$', msg.upper()):
            reservation_id = msg.upper()
            if check_reservation_exists(reservation_id):
                session_data['reservation_id'] = reservation_id
                # Suppression de la réservation dans la base de données
                cursor.execute("DELETE FROM reservations WHERE reservation_id=%s", (reservation_id,))
                conn.commit()
                session_data = reset_session_data(session_data)
                save_user_session(user_id, session_data)
                return f"La réservation {reservation_id} a été annulée avec succès.\n\n{random.choice(get_responses('reprise_apres_action'))}"
            else:
                return "Aucune réservation trouvée avec ce numéro. Veuillez vérifier et réessayer."
        else:
            return "Format de numéro de réservation invalide. Veuillez entrer un numéro de réservation valide (ex: RES00001)."
    
    else:
        session_data = reset_session_data(session_data)
        save_user_session(user_id, session_data)
        return "Désolé, une erreur est survenue. La session a été réinitialisée. Veuillez réessayer."

def handle_extend_intent(tag, msg, user_id, session_data):
    step = session_data.get('step', 'none')
    
    if step == 'demande_numero_reservation_extend':
        if re.match(r'^RES\d{5}$', msg.upper()):
            reservation_id = msg.upper()
            if check_reservation_exists(reservation_id):
                session_data['reservation_id'] = reservation_id
                session_data['step'] = 'demande_dates_prolongation'
                save_user_session(user_id, session_data)
                return "Veuillez indiquer la nouvelle date de départ (format JJ/MM/AAAA)."
            else:
                return "Aucune réservation trouvée avec ce numéro. Veuillez vérifier et réessayer."
        else:
            return "Format de numéro de réservation invalide. Veuillez entrer un numéro de réservation valide (ex: RES00001)."

    elif step == 'demande_dates_prolongation':
        date_checkout = validate_date(msg)
        if date_checkout:
            session_data['new_checkout_date'] = msg
            reservation_id = session_data.get('reservation_id')
            
            if not reservation_id:
                return "Désolé, nous n'avons pas trouvé votre réservation. Veuillez fournir votre numéro de réservation à nouveau."

            try:
                cursor.execute("UPDATE reservations SET date_checkout=%s WHERE reservation_id=%s",
                               (convert_date_format(date_checkout), reservation_id))
                conn.commit()
                session_data = reset_session_data(session_data)
                save_user_session(user_id, session_data)
                return f"La date de départ pour la réservation {reservation_id} a été prolongée avec succès au {msg}.\n\n{random.choice(get_responses('reprise_apres_action'))}"
            except mysql.connector.Error as err:
                logging.error(f"Erreur lors de la mise à jour de la réservation : {err}")
                session_data = reset_session_data(session_data)
                save_user_session(user_id, session_data)
                return "Désolé, une erreur est survenue lors de la prolongation de la réservation. Veuillez réessayer plus tard."
        else:
            return "Format de date invalide. Veuillez entrer la date au format JJ/MM/AAAA."
    
    else:
        session_data = reset_session_data(session_data)
        save_user_session(user_id, session_data)
        return "Désolé, une erreur est survenue. La session a été réinitialisée. Veuillez réessayer."

def handle_feedback_intent(tag, msg, user_id, session_data):
    step = session_data.get('step', 'none')
    if step == 'feedback_rating':
        try:
            feedback = int(msg)
            if 1 <= feedback <= 5:
                save_feedback(user_id, session_data.get('last_question', ''), session_data.get('last_bot_response', ''), feedback)
                session_data = reset_session_data(session_data)
                save_user_session(user_id, session_data)
                return random.choice(get_responses('feedback_note')) + "\n\n" + random.choice(get_responses('reprise_apres_action'))
            else:
                return "Veuillez entrer une note entre 1 et 5."
        except ValueError:
            return "Veuillez entrer une note valide entre 1 et 5."
    else:
        session_data = reset_session_data(session_data)
        save_user_session(user_id, session_data)
        return random.choice(get_responses('indefini')) + "\n\n" + random.choice(get_responses('reprise_apres_action'))

def get_response(msg, user_id):
    session_data = get_user_session(user_id)
    session_data['history'].append({'user': msg})

    logging.info(f"Session avant traitement: {session_data}")

    if 'last_question' in session_data and session_data['last_question'].lower() == msg.lower():
        response = "Vous avez déjà mentionné cela. Essayez de formuler autrement ou fournissez de nouvelles informations."
        session_data['history'].append({'bot': response})
        save_user_session(user_id, session_data)
        return response

    if 'step' in session_data and session_data['state'] != STATE['NONE']:
        current_state = session_data['state']
        logging.info(f"État actuel: {current_state}")
        response = handle_intent('current_step', msg, user_id, session_data)
        session_data['last_question'] = msg
        session_data['last_bot_response'] = response
        session_data['history'].append({'bot': response})
        save_user_session(user_id, session_data)
        return response

    sentence = tokenize(msg)
    X = bag_of_words(sentence, all_words)
    X = X.reshape(1, X.shape[0])
    X = torch.from_numpy(X).to(device)

    with torch.no_grad():
        output = model(X)
        _, predicted = torch.max(output, dim=1)
        tag = tags[predicted.item()]

        probs = F.softmax(output, dim=1)
        prob = probs[0][predicted.item()]

    logging.info(f"Input: {msg}")
    logging.info(f"Predicted Tag: {tag}, Confidence: {prob.item()}")

    threshold = 0.6
    if prob.item() > threshold:
        response = handle_intent(tag, msg, user_id, session_data)
        session_data['last_question'] = msg
        session_data['last_bot_response'] = response
    else:
        save_unknown_question(msg)
        response = "Je n'ai pas compris votre demande. Pouvez-vous être plus précis ?\n\n" + random.choice(get_responses('reprise_apres_action'))

    session_data['history'].append({'bot': response})
    save_user_session(user_id, session_data)

    logging.info(f"Réponse générée: {response}")
    return response
