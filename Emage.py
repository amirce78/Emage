# Imports
from PIL import Image as Im
from math import log2, ceil
from configparser import ConfigParser
from pathlib import Path

class Text:
    def __init__(self, path: str, cfg: ConfigParser) -> None:
        self.cfg = cfg

        self.path = path
        self.encoding = self.cfg["text"]["encoding"]
        self.n_lowest_bit = int(self.cfg["text"]["n_lowest_bit"])
        self.max_characters = int(self.cfg["text"]["max_characters"])
    
    def read(self) -> str:
        with open(file= self.path, mode= "r", encoding= self.encoding) as f:
            text = f.read()
            if len(text) > self.max_characters:
                raise OverflowError(f"Message length should be less than {self.max_characters} characters")
            else:
                return text
    
    def str_to_chunks(self, text: str) -> list:
        chunks = [] # Reserved bits & text
        mask = 2 ** self.n_lowest_bit - 1 # E.g., 2 ** 2 - 1 = 3 = 00000011
        reserved_bits  = ceil(log2(self.max_characters))

        for i in range(0, reserved_bits, self.n_lowest_bit):
            chunks.insert(0, (len(text) >> i) & mask) # E.g., 00001010 & 00000011 = 00000010 = 2

        for char in text:
            starting_point = len(chunks)
            for i in range(0, 8, self.n_lowest_bit): # 8: ascii
                chunks.insert(starting_point, (ord(char) >> i) & mask)
        
        return chunks

class Image:
    def __init__(self, im: Im, cfg: ConfigParser) -> None:
        self.image = im.convert(mode= "RGB")
        self.image_array = self.image.load()
        self.cfg = cfg

        self.n_lowest_bit = int(cfg["text"]["n_lowest_bit"])
        self.max_characters = int(cfg["text"]["max_characters"])
        self.reserved_bits = ceil(log2(self.max_characters))
    
    def encode(self, path: str, chunks: list) -> None:
        
        mask = 2 ** self.reserved_bits - 2 ** self.n_lowest_bit # E.g., 2 ** 8 - 2 ** 2 = 252 = 11111100
        for h in range(self.image.height):
            for w in range(self.image.width):
                self.image_array[w, h] = tuple([(val & mask) + chunks.pop(0) if chunks else val for val in self.image_array[w, h]])
                if not chunks:
                    break
            else:
                continue
            break

        # Create the directory if doesn't exist.
        Path("/".join(path.split("/")[:-1])).mkdir(exist_ok=True)
        self.image.save(fp= path, optimize= True, compress_level= 9)
    
    def decode_to_chunks(self) -> list:
        mask = 2 ** self.n_lowest_bit - 1 # E.g., 2 ** 2 - 1 = 3 = 00000011
        reserved_bits_counter = 0
        chunks = []
        total_characters = 0
        for h in range(self.image.height):
            for w in range(self.image.width):
                for c in range(3):
                    if reserved_bits_counter < ceil(self.reserved_bits / self.n_lowest_bit):
                        # total_characters += (self.image_array[w, h][c] & mask) << (self.reserved_bits - ((h*len(range(self.image.width))+1)*(w*len(self.image_array[w, h])+1)*(c+1)) * self.n_lowest_bit)
                        total_characters += (self.image_array[w, h][c] & mask) << (self.reserved_bits - (h*self.image.width*len(self.image_array[w, h]) + w*len(self.image_array[w, h]) + (c + 1)) * 2)
                        reserved_bits_counter += 1
                    elif len(chunks) < total_characters * 8 / self.n_lowest_bit:
                        chunks.append(self.image_array[w, h][c] & mask)
                    else:
                        break
                else:
                    continue
                break
            else:
                continue
            break

        return chunks
    
    def chunks_to_text(self, path:str,  chunks: list) -> None:
        step = ceil(8 / self.n_lowest_bit)
        encode_characters = [chunks[i:i+step] for i in range(0, len(chunks), step)]
        decode_characters = []
        
        for char in encode_characters:
            temp = 0
            for i in range(len(char)):
                temp += (char[i] << (8 - self.n_lowest_bit * (i+1)))
            decode_characters.append(chr(temp))

        # Create the directory if doesn't exist.
        Path("/".join(path.split("/")[:-1])).mkdir(exist_ok=True)
        with open(file= path, mode= "w", encoding= self.cfg["text"]["encoding"]) as f:
            f.write("".join(decode_characters))

if __name__ == "__main__":
    # Load confings
    config = ConfigParser()
    config.read("./configs.ini")

    # Paths
    original_image_path = r"./input/image.png"
    original_text_path  = r"./input/text.txt"
    encoded_image_path  = r"./output/image.png"
    decoded_text_path   = r"./output/text.txt"

    # Text
    text_obj = Text(path= original_text_path, cfg= config)
    text = text_obj.read()
    chunks = text_obj.str_to_chunks(text)

    # Encode
    image = Im.open(fp= original_image_path)
    img = Image(im= image, cfg= config)
    img.encode(path= encoded_image_path, chunks= chunks)

    # Decode
    image = Im.open(fp= encoded_image_path)
    img = Image(im= image, cfg= config)
    chunks = img.decode_to_chunks()
    img.chunks_to_text(path= decoded_text_path, chunks= chunks)