# -*- coding: utf-8 -*-

import argparse
from utils import str2bool
from toolkit import VideoProcessor
import os


functions_dict = {
    "trim_by_silence": VideoProcessor.trim_by_silence,
    "denoise": VideoProcessor.denoise_video,
    "transcript": VideoProcessor.generate_transcript,
    "subtitles": VideoProcessor.add_subtitles,
    "save_separated_video": VideoProcessor.save_separated_video,
    "save_join": VideoProcessor.save_joined_video,
    "save_video": VideoProcessor.save_video,
    "set_vertical": VideoProcessor.set_vertical,
    "set_horizontal": VideoProcessor.set_horizontal,
    "apply_gain": VideoProcessor.apply_gain,
    "openai_process": VideoProcessor.openai_process,
    "split_video": VideoProcessor.split_video,
    "combine_fragments": VideoProcessor.combine_fragments,
}


parser = argparse.ArgumentParser(
    description="Multiples tools for video editing")
parser.add_argument(
    "input_file", type=str, nargs="+", help="The video file you want modified"
)

parser.add_argument('--split_size', type=int, default=200,
                    help='Size en MB para dividir el video antes del procesamiento.')

parser.add_argument('--combine', action='store_true',
                    help='Combina fragmentos de video despues del procesamiento.')


parser.add_argument(
    "-g", "--gain_factor", type=float, default=1.0,
    help="Factor to amplify the audio volume. E.g., 2.0 doubles the volume, 0.5 halves it."
)


parser.add_argument(
    "--pipeline",
    type=str,
    nargs="+",
    help=f"Functions to be applied to the video, {', '.join(functions_dict.keys())}",
)

parser.add_argument(
    "-c", "--clip_interval", type=float, default=2, help="The precision of the trimming"
)
parser.add_argument(
    "-s",
    "--sound_threshold",
    type=float,
    default=0.01,
    help="Maximun amout of volume to be considerer as silence",
)
parser.add_argument(
    "-d",
    "--discard_silence",
    const=True,
    default=False,
    type=str2bool,
    nargs="?",
    help="Discard silence clips",
)
parser.add_argument(
    "--use_openai",
    const=True,
    default=False,
    type=str2bool,
    nargs="?",
    help="Decide if you want to process the video using OpenAI",
)


args = parser.parse_args()

gain_factor = args.gain_factor
use_openai = args.use_openai


if __name__ == "__main__":
    input_files = args.input_file
    pipeline = args.pipeline
    split_size = args.split_size
    should_combine = args.combine
    clip_interval = args.clip_interval
    sound_threshold = args.sound_threshold
    discard_silence = args.discard_silence

    video_processor = VideoProcessor()

    for input_file in input_files:
        fragments = []
        if split_size:
            # Dividir el video en fragmentos si es necesario
            print(f"Dividiendo {input_file} en fragmentos...")
            fragments = VideoProcessor.split_video(input_file, split_size)
            print(f"Fragmentos creados: {fragments}")

        # Procesar cada fragmento (o el video completo si no se dividió)
        videos_to_process = fragments if fragments else [input_file]

        for video in videos_to_process:
            print(f"Comenzando procesamiento de {video}...")
            kwargs = {
            "video_path": video,
            "clip_interval": clip_interval,
            "sound_threshold": sound_threshold,
            "discard_silence": discard_silence,
            "gain_factor": gain_factor,
        }

        kwargs = video_processor.get_video_data(**kwargs)

        for step_in_pipeline in pipeline:
            if step_in_pipeline not in functions_dict:
                raise ValueError(
                    f"Function {step_in_pipeline} not found. Available functions: {', '.join(functions_dict.keys())}"
                )

            print(f"Aplicando {step_in_pipeline} a {input_file}...")
            kwargs = functions_dict[step_in_pipeline](**kwargs)
            print(f"Finalizado {step_in_pipeline} para {input_file}")

            # Luego de que todas las funciones del pipeline han sido aplicadas al video
        if use_openai:
            print(f"Aplicando openai_process a {input_file}")
            kwargs = functions_dict["openai_process"](**kwargs)
            print(f"openai_process completado para {input_file}")
            
        # Combinar fragmentos después de procesar si es necesario
        combined_output_file = None
        if should_combine and fragments:
            combined_output_file = input_file.replace('.mp4', '_combined.mp4')
            print(f"Combinando fragmentos en {combined_output_file}...")
            VideoProcessor.combine_fragments(fragments, combined_output_file)
            print(f"Procesamiento completado para {video}")
            # Actualizar kwargs con el video combinado
            kwargs = {
                "video_path": combined_output_file,
            }
            kwargs = video_processor.get_video_data(**kwargs)
        else:
            combined_output_file = input_file
        
        # Aplicar funciones que deben ejecutarse después de la combinación
        post_combine_functions = ["transcript"]  
        for func in post_combine_functions:
            if func in functions_dict:
                print(f"Aplicando {func} a {combined_output_file}...")
                kwargs = functions_dict[func](**kwargs)
                print(f"Finalizado {func} para {combined_output_file}")
    
        # Despues de procesar todos los pasos del pipeline para todos los archivos de entrada
        for input_file in input_files:
            print(f"Comenzando a procesar el archivo {input_file}...")
            audio_file_name = f"{input_file.split('/')[-1].split('.')[0]}_audio.wav"
            denoised_file_name = f"{input_file.split('/')[-1].split('.')[0]}_denoised.wav"

            print(f"Intentando eliminar {audio_file_name} y {denoised_file_name}...")

    if os.path.exists(audio_file_name):
        os.remove(audio_file_name)
        print(f"Eliminado {audio_file_name}")

    if os.path.exists(denoised_file_name):
        os.remove(denoised_file_name)
        print(f"Deleted {denoised_file_name}")