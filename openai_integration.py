# -*- coding: utf-8 -*-

import openai
import os
openai.api_key = os.getenv('OPENAI_API_KEY')


def generate_metadata_from_transcription(transcription):
    print("Transcripcion recibida:", transcription)
    
    # Formulamos una conversacion con el modelo en español
    conversation_payload = {
        "messages": [
            {"role": "system", "content": "Eres un asistente util y experimentado."},
            {"role": "user", "content": f"Basandote en el siguiente resumen de video, proporciona un titulo, descripcion y hashtags: {transcription}"}
        ]
    }
    
    # Usamos el endpoint correcto para el modelo de chat
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=conversation_payload["messages"]
    )
    
    # Procesar la respuesta 
    assistant_response = response.choices[0].message['content']

    # Aquí va el nuevo bloque de código:
    lines = assistant_response.split('\n')
    if len(lines) != 3:
        # Maneja el caso en que no se recibieron exactamente tres lineas
        print("Respuesta inesperada del modelo:", assistant_response)
        return None, None, None  # O maneja este caso como prefieras
    title, description, raw_hashtags = lines

    hashtags = raw_hashtags.split()
    return title, description, hashtags




def save_to_txt(filename, title, description, hashtags):
    with open(filename, 'w') as file:
        file.write("Titulo:\n" + title + "\n\n")
        file.write("Descripcion:\n" + description + "\n\n")
        file.write("Hashtags:\n" + ' '.join(hashtags))
