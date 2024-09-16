# train.py

import numpy as np
import json
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from nltk_utils import bag_of_words, tokenize, stem, stop_words
from model import NeuralNet
from sklearn.model_selection import train_test_split

# Charger les intentions
with open('intents.json', 'r', encoding='utf-8') as f:
    intents = json.load(f)

all_words = []
tags = []
xy = []
# Parcours des phrases modèles
for intent in intents['intents']:
    tag = intent['tag']
    tags.append(tag)
    for pattern in intent['patterns']:
        # Tokenisation
        w = tokenize(pattern)
        all_words.extend(w)
        xy.append((w, tag))

# Stemming et minuscule pour chaque mot
ignore_words = ['?', '!', '.', ',', ':', ';']
all_words = [stem(w) for w in all_words if w not in ignore_words and w not in stop_words]
# Suppression des doublons et tri
all_words = sorted(set(all_words))
tags = sorted(set(tags))

# Création des données d'entraînement
X_train = []
y_train = []
for (pattern_sentence, tag) in xy:
    # X : bag of words
    bag = bag_of_words(pattern_sentence, all_words)
    X_train.append(bag)
    # y : index du tag
    label = tags.index(tag)
    y_train.append(label)

X_train = np.array(X_train)
y_train = np.array(y_train)

# Séparer les données en train et test (optionnel mais recommandé)
X_train, X_test, y_train, y_test = train_test_split(X_train, y_train, test_size=0.2, random_state=42)

# Hyperparamètres
num_epochs = 2000
batch_size = 8
learning_rate = 0.001
input_size = len(X_train[0])
hidden_size = 8
output_size = len(tags)

print(f"Entraînement avec {num_epochs} époques, batch size {batch_size}, learning rate {learning_rate}")
print(f"Input size: {input_size}, Output size: {output_size}")

class ChatDataset(Dataset):

    def __init__(self, X, y):
        self.n_samples = len(X)
        self.x_data = X
        self.y_data = y

    # Supporte l'indexation pour dataset[i]
    def __getitem__(self, index):
        return self.x_data[index], self.y_data[index]

    # Retourne la taille du dataset
    def __len__(self):
        return self.n_samples

dataset = ChatDataset(X_train, y_train)
train_loader = DataLoader(dataset=dataset,
                          batch_size=batch_size,
                          shuffle=True,
                          num_workers=0)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

model = NeuralNet(input_size, hidden_size, output_size).to(device)

# Fonction de perte et optimiseur
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

# Entraînement du modèle
for epoch in range(num_epochs):
    for (words, labels) in train_loader:
        words = words.to(device)
        labels = labels.to(dtype=torch.long).to(device)

        # Forward pass
        outputs = model(words)
        loss = criterion(outputs, labels)

        # Backward et optimisation
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    if (epoch+1) % 100 == 0:
        print (f'Époque [{epoch+1}/{num_epochs}], Perte: {loss.item():.4f}')

print(f'Perte finale: {loss.item():.4f}')

data = {
    "model_state": model.state_dict(),
    "input_size": input_size,
    "hidden_size": hidden_size,
    "output_size": output_size,
    "all_words": all_words,
    "tags": tags
}

FILE = "data.pth"
torch.save(data, FILE)

print(f'Entraînement terminé. Modèle sauvegardé dans {FILE}')
