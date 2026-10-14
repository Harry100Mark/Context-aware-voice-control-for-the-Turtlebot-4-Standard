import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_msgs.msg import ByteMultiArray
import os
import tempfile
import assemblyai as aai
import wave  # Neu für WAV-Header

class TranscriberNode(Node):
    def __init__(self):
        super().__init__('transcriber')
        self.subscription = self.create_subscription(
            ByteMultiArray,
            '/audio_file',
            self.audio_file_callback,
            10)
        self.publisher = self.create_publisher(String, '/transcribed_text', 10)
        # AssemblyAI API Key
        api_key = os.getenv('ASSEMBLYAI_API_KEY')
        if not api_key:
            self.get_logger().error('ASSEMBLYAI_API_KEY is not set')
            return
        aai.settings.api_key = api_key
        # Transcription config for German navigation commands
        self.config = aai.TranscriptionConfig(
            language_code="de",
            word_boost=[
                "fahre:10", "fahr:10", "dreh:10", "drehe:10", "Turtlebot:10",
                "links:10", "rechts:10", "geradeaus:10", "vorwärts:10", "rückwärts:10",
                "Meter:10", "Zentimeter:10", "Grad:10", "stop:10", "halte:10",
                "langsamer:10", "schneller:10", "abbiegen:10", "Kurve:10",
                "komm:10", "bieg:10", "beweg:10", "zum:10", "hinter:10",
                "neben:10", "am:10", "vorbei:10", "nach:10", "um:10",
                "die:10", "Ecke:10", "Ausgang:10", "Schrank:10",
                "Pepper:10", "Tisch:10", "Karton:10", "Stuhl:10",
                "runder Tisch:10", "Regal:10", "Kommode:10", "Telefon:10",
                "Mülleimer:10", "Tür:10", "Fenster:10", "Wand:10",
                "Whiteboard:10", "Arbeitsplatz:10", "Computer:10", "Pc:10"
            ]
        )
    def audio_file_callback(self, msg):
        self.get_logger().info('Receiving audio data...')
        try:
            audio_bytes = bytes((int(b) & 0xFF for b in msg.data))
            self.get_logger().info(f'Received audio data: {len(audio_bytes)} Bytes')
        except Exception as e:
            self.get_logger().error(f'Could not decode audio data: {e}')
            return
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            temp_audio_path = temp_audio.name
        try:
            # Erstelle gültige WAV-Datei mit Header
            with wave.open(temp_audio_path, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)  # 16 Bit
                wf.setframerate(16000)  # Samplerate aus Recorder
                wf.writeframes(audio_bytes)
        except Exception as e:
            self.get_logger().error(f'Could not create WAV file: {e}')
            os.unlink(temp_audio_path)
            return
        try:
            transcriber = aai.Transcriber(config=self.config)
            transcript = transcriber.transcribe(temp_audio_path)
            if transcript.error:
                self.get_logger().error(f'Transcription error: {transcript.error}')
                text = ''
            else:
                text = transcript.text.strip()
        except Exception as e:
            self.get_logger().error(f'Transcription failed: {e}')
            text = ''
        finally:
            os.unlink(temp_audio_path)
        if text:
            self.publisher.publish(String(data=text))
            self.get_logger().info(f'Transcribed text: {text}')
def main(args=None):
    rclpy.init(args=args)
    node = TranscriberNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
if __name__ == '__main__':
    main()