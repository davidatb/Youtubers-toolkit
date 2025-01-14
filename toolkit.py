import numpy as np
import moviepy.editor as editor
from moviepy.editor import VideoFileClip
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.audio.fx import volumex
from openai_integration import generate_metadata_from_transcription, save_to_txt
from tqdm import tqdm


class VideoProcessor:
    
    @staticmethod
    def openai_process(**kwargs):
        transcript_file_name = kwargs["transcript_file_name"]
        
        with open(transcript_file_name, 'r') as file:
            transcript = file.read()
            
        title, description, hashtags = generate_metadata_from_transcription(transcript)
        
        # Guarda los resultados en un txt o de la forma que prefieras
        # Tambi�n puedes agregar los resultados a kwargs y retornarlos si es necesario.
        save_to_txt(f"{kwargs['filename']}_metadata.txt", title, description, hashtags)
        
        return kwargs

    @staticmethod
    def apply_gain(**kwargs):
        input_video_file_clip = kwargs["input_video_file_clip"]
        gain_factor = kwargs.get("gain_factor", 1.0)  # 1.0 means no change

        # Apply gain to the audio
        amplified_audio = input_video_file_clip.audio.fx(
            volumex.volumex, gain_factor)
        input_video_file_clip = input_video_file_clip.set_audio(
            amplified_audio)

        kwargs["input_video_file_clip"] = input_video_file_clip
        return kwargs

    @staticmethod
    def _get_subclip_volume(subclip, second, interval):
        cut = subclip.subclip(
            second, second + interval).audio.to_soundarray(fps=44100)
        return np.sqrt(((1.0 * cut) ** 2).mean())

    @staticmethod
    def _float_to_srt_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:02d}"

    @staticmethod
    def _get_audio(input_video_file_clip, filename):
        audio_file_name = f"{filename}_audio.wav"

        import os

        if os.path.exists(audio_file_name):
            os.remove(audio_file_name)

        input_video_file_clip.audio.write_audiofile(
            audio_file_name, codec="pcm_s16le")
        return audio_file_name

    @staticmethod
    def save_video(**kwargs):
        filename = kwargs["filename"]
        input_video_file_clip = kwargs["input_video_file_clip"]

        clip_name = f"{filename}_EDITED.mp4"

        input_video_file_clip.write_videofile(clip_name, audio_codec="aac")
        kwargs["clips_name"] = clip_name
        return kwargs

    @staticmethod
    def save_joined_video(**kwargs):
        if "clips" not in kwargs:
            return VideoProcessor.save_video(**kwargs)

        filename = kwargs["filename"]
        clips = kwargs["clips"]
        clip_name = f"{filename}_EDITED.mp4"
        if isinstance(clips, list):
            concat_clip = editor.concatenate_videoclips(clips)
            concat_clip.write_videofile(clip_name, audio_codec="aac")
            kwargs["clips_name"] = clip_name
            return kwargs

        clips.write_videofile(clip_name, audio_codec="aac")
        kwargs["clips_name"] = clip_name
        return kwargs

    @staticmethod
    def save_separated_video(**kwargs):
        if "clips" not in kwargs:
            return VideoProcessor.save_video(**kwargs)

        filename = kwargs["filename"]
        clips = kwargs["clips"]
        clips_format = "{filename}_EDITED_{i}.mp4"

        for i, clip in enumerate(clips):
            clip.write_videofile(
                clips_format.format(filename=filename, i=i), audio_codec="aac"
            )

        kwargs["clips_name"] = clips_format.format(filename=filename, i="{i}")
        return kwargs

    @staticmethod
    def generate_transcript(**kwargs):
        import whisper

        input_video_file_clip, filename = (
            kwargs["input_video_file_clip"],
            kwargs["filename"],
        )

        audio_file_name = VideoProcessor._get_audio(
            input_video_file_clip, filename)

        model = whisper.load_model("base")
        results = model.transcribe(audio_file_name)
        transcript = ""
        for result in results["segments"]:
            start_date = VideoProcessor._float_to_srt_time(result["start"])
            end_date = VideoProcessor._float_to_srt_time(result["end"])
            text_data = result["text"].strip()

            transcript += (
                f"{result['id'] + 1}\n{start_date} --> {end_date}\n{text_data}\n\n"
            )

        transcript_file_name = f"{filename}_transcript.srt"
        with open(transcript_file_name, "w") as file:
            file.write(transcript)

        kwargs["transcript_file_name"] = transcript_file_name
        return kwargs

    @staticmethod
    def denoise_video(**kwargs):
        import torch
        import torchaudio
        from denoiser import pretrained
        from denoiser.dsp import convert_audio

        input_video_file_clip, filename = (
            kwargs["input_video_file_clip"],
            kwargs["filename"],
        )

        audio_file_name = VideoProcessor._get_audio(
            input_video_file_clip, filename)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = pretrained.dns64().to(device)
        wav, source = torchaudio.load(audio_file_name)
        wav = convert_audio(wav.to(device), source,
                            model.sample_rate, model.chin)
        with torch.no_grad():
            denoised = model(wav[None])[0]

        denoised_file_name = f"{filename}_denoised.wav"
        torchaudio.save(denoised_file_name, denoised.cpu(), model.sample_rate)
        # replace audio in video
        input_video_file_clip.audio = editor.AudioFileClip(denoised_file_name)

        kwargs["input_video_file_clip"] = input_video_file_clip
        return kwargs

    @staticmethod
    def add_subtitles(**kwargs):
        filename = kwargs["filename"]
        input_video_file_clip = kwargs["input_video_file_clip"]
        subtitles_filename = kwargs.get(
            "transcript_file_name", f"{filename}_transcript.srt"
        )

        def generator(txt):
            return editor.TextClip(
                txt,
                font="Arial",
                fontsize=28,
                color="white",
                method="caption",
                align="south",
                bg_color="black",
            )

        subtitles = SubtitlesClip(subtitles_filename, generator)
        video_list = [input_video_file_clip,
                      subtitles.set_pos(("center", "bottom"))]
        video_with_subs = editor.CompositeVideoClip(video_list)

        kwargs["input_video_file_clip"] = video_with_subs
        return kwargs

    @staticmethod
    def set_vertical(**kwargs):
        input_video_file_clip = kwargs["input_video_file_clip"]
        shape = input_video_file_clip.size

        if shape[0] > shape[1]:
            shape = [shape[1], shape[0]]
            input_video_file_clip = input_video_file_clip.resize(shape)

        kwargs["shape"] = input_video_file_clip.size
        kwargs["input_video_file_clip"] = input_video_file_clip
        return kwargs

    @staticmethod
    def set_horizontal(**kwargs):
        input_video_file_clip = kwargs["input_video_file_clip"]
        shape = input_video_file_clip.size

        if shape[0] < shape[1]:
            shape = [shape[1], shape[0]]
            input_video_file_clip = input_video_file_clip.resize(shape)

        kwargs["shape"] = input_video_file_clip.size
        kwargs["input_video_file_clip"] = input_video_file_clip
        return kwargs

    @staticmethod
    def get_video_data(**kwargs):
        video_path = kwargs["video_path"]

        filename = video_path.split("/")[-1].split(".")[0]
        input_video_file_clip = VideoFileClip(video_path)

        kwargs["shape"] = input_video_file_clip.size
        kwargs["filename"] = filename
        kwargs["input_video_file_clip"] = input_video_file_clip
        return kwargs

    @staticmethod
    def trim_by_silence(**kwargs):
        input_video_file_clip = kwargs["input_video_file_clip"]
        clip_interval = kwargs["clip_interval"]
        sound_threshold = kwargs["sound_threshold"]
        discard_silence = kwargs["discard_silence"]

        print("Chunking video...")
        volumes = []
        for i in tqdm(np.arange(0, input_video_file_clip.duration, clip_interval)):
            if input_video_file_clip.duration <= i + clip_interval:
                continue
            volumes.append(
                VideoProcessor._get_subclip_volume(
                    input_video_file_clip, i, clip_interval
                )
            )

        print("Processing silences...")
        volumes = np.array(volumes)
        volumes_binary = volumes > sound_threshold

        change_times = [0]
        for i in range(1, len(volumes_binary)):
            if volumes_binary[i] == volumes_binary[i - 1]:
                continue
            change_times.append(i * clip_interval)
        change_times.append(input_video_file_clip.duration)

        print("Subclipping...")
        first_piece_silence = 1 if volumes_binary[0] else 0
        clips = []
        for i in range(1, len(change_times)):
            if discard_silence and i % 2 != first_piece_silence:
                continue
            new = input_video_file_clip.subclip(
                change_times[i - 1], change_times[i])
            clips.append(new)

        kwargs["clips"] = clips
        return kwargs
