# Parâmetros para configuração do programa do filtro
parameters = {
"volume_total":500000,  # Contador para o volume total que passou pelo filtro, em mL
"volume_base":250,      # Seta o volume inicial do objeto encoder toda vez que o sistema reinicializa, em mL
"volume_max":1000,      # Volume máximo permitido, em mL
"volume_fast_fill":950, # Volume aplicado quando o botão azul é pressionado, em mL
"timeout":45            # Tempo que o sistema fica acordado até desligar o display e resetar o volume do encoder, em s
}
