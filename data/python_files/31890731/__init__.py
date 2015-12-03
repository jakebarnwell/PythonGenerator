import base
import block
import engine
import group
import playfield
import sprite
import state
import tetromino
import text

def Leftsnake(color):
    return tetromino.Tetromino(color, "leftsnake", ("    \n"
                                                    "    \n"
                                                    " ## \n"
                                                    "  ##\n"))

def Rightsnake(color):
    return tetromino.Tetromino(color, "rightsnake", ("    \n"
                                                     "    \n"
                                                     " ## \n"
                                                     "##  \n"))

def Stick(color):
    return tetromino.Tetromino(color, "stick", (" #  \n"
                                                " #  \n"
                                                " #  \n"
                                                " #  \n"))

def Square(color):
    tetro = tetromino.Tetromino(color, "square", ("    \n"
                                                  "    \n"
                                                  " ## \n"
                                                  " ## \n"))
    def func(direction):
        pass
    tetro.rotate = func
    return tetro

def Leftgun(color):
    return tetromino.Tetromino(color, "leftgun", ("    \n"
                                                  "  # \n"
                                                  "  # \n"
                                                  " ## \n"))

def Rightgun(color):
    return tetromino.Tetromino(color, "rightgun", ("    \n"
                                                   " #  \n"
                                                   " #  \n"
                                                   " ## \n"))

def Tee(color):
    return tetromino.Tetromino(color, "tee", ("    \n"
                                              "    \n"
                                              "  # \n"
                                              " ###\n"))

tetromino_classes = [Leftsnake, Rightsnake, Stick, Square, 
                     Leftgun, Rightgun, Tee]

