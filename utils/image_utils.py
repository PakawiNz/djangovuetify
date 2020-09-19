from typing import Iterable

from PIL import Image
from pdf2image import convert_from_path


def convert_pdf_to_images(input_file):
    return convert_from_path(file_path)


def save_images_as_pdf(input_files:Iterable, output_file:str):
    if not output_file.endswith('.pdf'):
        output_file = output_file + '.pdf'

    images = []
    for path in input_files:
        images.append(Image.open(path).convert('RGB'))

    images[0].save(output_file, save_all=True, append_images=images[1:])
    return output_file

