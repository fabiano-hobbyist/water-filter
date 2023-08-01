from myconf import *

menu = {
    (0) : ["1 Exibir volume", "  total"],
    (10): ["2 Ajustar volume", "  inicial"],
    (20): ["3 Ajustar volume", "  maximo"],
    (30): ["4 Ajustar volume", "  fast fill"],
    (40): ["5 Ajustar tempo", "  para timeout"],
    (50): ["6 Restaurar", "  padroes"],
    (60): ["Retornar"],
    }

default = {
    "volume_total":parameters['volume_total'],
    "volume_base":250,
    "volume_max":1000,
    "volume_fast_fill":950,
    "timeout":45
    }