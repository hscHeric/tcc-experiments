# Opcoes de build e feature flags

option(HSCOPT_ENABLE_OPENMP "Habilita OpenMP quando disponivel" ON)
option(HSCOPT_ENABLE_LTO "Habilita IPO/LTO quando suportado" ON)
option(HSCOPT_ENABLE_NATIVE "Habilita -march=native/-mtune=native" ON)
option(HSCOPT_ENABLE_FAST_MATH "Habilita fast-math (pode mudar resultados)" OFF)
option(HSCOPT_ENABLE_WARNINGS "Habilita avisos do compilador" ON)
option(HSCOPT_ENABLE_STRICT_ALIASING "Habilita -fstrict-aliasing" ON)
option(HSCOPT_ENABLE_VISIBILITY_HIDDEN "Habilita -fvisibility=hidden" ON)
option(HSCOPT_BUILD_EXAMPLES "Compila executaveis de exemplo" ON)

# Flags futuras (feature flags) - reserve este namespace
# option(HSCOPT_FEATURE_X "Descricao" OFF)
