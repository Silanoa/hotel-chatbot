from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from chatbot_env import ChatbotEnv
import torch

FILE = "data.pth"
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
data = torch.load(FILE, map_location=device)

tags = data['tags']
input_size = data['input_size']

# Créer l'environnement avec les tags et l'input_size
env = ChatbotEnv(tags, input_size)

# Définir le modèle PPO
model = PPO('MlpPolicy', env, verbose=1)

# Définir un callback pour sauvegarder périodiquement le modèle
checkpoint_callback = CheckpointCallback(save_freq=1000, save_path='./models/',
                                         name_prefix='chatbot_model_rl')

# Entraîner le modèle
model.learn(total_timesteps=10000, callback=checkpoint_callback)

# Sauvegarder le modèle final
model.save("chatbot_model_rl")
