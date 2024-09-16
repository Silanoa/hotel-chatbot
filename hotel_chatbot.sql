CREATE DATABASE IF NOT EXISTS hotel_chatbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE hotel_chatbot;

CREATE TABLE IF NOT EXISTS clients (
    client_id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(255) NOT NULL,
    prenom VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    telephone VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS chambres (
    chambre_id INT AUTO_INCREMENT PRIMARY KEY,
    type_chambre VARCHAR(50) NOT NULL,
    prix DECIMAL(10,2) NOT NULL,
    est_disponible BOOLEAN NOT NULL DEFAULT TRUE,
    INDEX idx_type_chambre (type_chambre)
);

CREATE TABLE IF NOT EXISTS reservations (
    reservation_id VARCHAR(10) PRIMARY KEY,
    client_id INT NOT NULL,
    chambre_id INT NOT NULL,
    date_checkin DATE NOT NULL,
    date_checkout DATE NOT NULL,
    date_reservation DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE CASCADE,
    FOREIGN KEY (chambre_id) REFERENCES chambres(chambre_id) ON DELETE CASCADE,
    INDEX idx_reservation_id (reservation_id) 
);

CREATE TABLE IF NOT EXISTS questions_inconnues (
    question_id INT AUTO_INCREMENT PRIMARY KEY,
    question_text TEXT NOT NULL,
    date_recue DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
    user_id VARCHAR(255) PRIMARY KEY,
    session_data TEXT,
    last_active DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedbacks (
    feedback_id INT AUTO_INCREMENT PRIMARY KEY,
    question_text TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    user_feedback INT NOT NULL,
    user_id VARCHAR(255),
    date_recue DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_sessions(user_id) ON DELETE SET NULL
);

INSERT INTO chambres (type_chambre, prix) VALUES ('Simple', 80.00);
INSERT INTO chambres (type_chambre, prix) VALUES ('Double', 120.00);
INSERT INTO chambres (type_chambre, prix) VALUES ('Suite', 200.00);