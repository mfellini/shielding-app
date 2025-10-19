import streamlit as st
import math
import numpy as np
from scipy.interpolate import interp1d


# ====================================================================
# 1. DATI NCRP 147 CONSOLIDATI E TABELLE RAMO 4
# ====================================================================


# Struttura dati unificata per Modalità Radiografica (RAMO 1/2/4)
# Include Kp1 (Primario), Wnorm (Carico di Lavoro), e le 3 componenti Ksec1 (Secondario/Fuga)
# I valori di Ksec1 (LeakSide, ForBack, Comb) e Wnorm sono da Tabella 4.7, Kp1 da Tabella 4.5.
KERMA_DATA = {
    # 1. STANZA RADIOGRAFICA (TUTTE BARRIERE)
    "STANZA RADIOGRAFICA (TUTTE BARRIERE)": {
        'Wnorm': 2.5,
        'Kp1': None, # Usato per barriere secondarie/generiche (Kp1 da Tab 4.5 non applicabile qui)
        'Ksec1_LeakSide': 3.4e-2, # 3.4*10^-2
        'Ksec1_ForBack': 4.8e-2, # 4.8*10^-2
        'Ksec1_Comb': 4.9e-2,    # VALORE COMBINATO
    },
    # 2. STANZA RADIOGRAFICA GENERICA (CHEST BUCKY - PARETE PRIMARIA)
    "STANZA RADIOGRAFICA (CHEST BUCKY)": {
        'Wnorm': 0.60,
        'Kp1': 2.3, # Kp1 da Tab 4.5
        'Ksec1_LeakSide': 5.3e-3, # 5.3*10^-3
        'Ksec1_ForBack': 6.9e-3, # 6.9*10^-3
        'Ksec1_Comb': 7.3e-3,
    },
    # 3. STANZA RADIOGRAFICA (PAVIMENTO/ALTRE BARRIERE - ES: PARETE PRIMARIA)
    "STANZA RADIOGRAFICA (PIANO/ALTRE BARRIERE)": {
        'Wnorm': 1.9,
        'Kp1': 5.2, # Kp1 da Tab 4.5
        'Ksec1_LeakSide': 2.3e-2, # 2.3*10^-2
        'Ksec1_ForBack': 3.3e-2, # 3.3*10^-2
        'Ksec1_Comb': 3.3e-2,
    },
    # 4. TUBO FLUOROSCOPICO STANZA R&F
    "FLUOROSCOPIA (R&F)": {
        'Wnorm': 13.0,
        'Kp1': 5.9, # Kp1 da Tab 4.5 (Usato se la barriera R&F è considerata primaria/pavimento)
        'Ksec1_LeakSide': 3.2e-1, # 3.2*10^-1
        'Ksec1_ForBack': 4.4e-1, # 4.4*10^-1
        'Ksec1_Comb': 4.6e-1,
    },
    # 5. TUBO RADIOGENO STANZA R&F
    "RADIOGRAFIA (TUBO R&F)": {
        'Wnorm': 1.5,
        'Kp1': None, # Usato per barriere secondarie
        'Ksec1_LeakSide': 2.9e-2, # 2.9*10^-2
        'Ksec1_ForBack': 3.9e-2, # 3.9*10^-2
        'Ksec1_Comb': 4.0e-2, # Corretto 4.0*0-2 a 4.0*10^-2
    },
    # 6. STANZA RADIOGRAFICA TORACE
    "STANZA RADIOGRAFICA TORACE": {
        'Wnorm': 0.22,
        'Kp1': 1.2, # Kp1 da Tab 4.5 (Se la barriera è primaria)
        'Ksec1_LeakSide': 2.7e-3, # 2.7*10^-3
        'Ksec1_ForBack': 3.2e-3, # 3.2*10^-3
        'Ksec1_Comb': 3.6e-3,
    },
    # 7. MAMMOGRAFIA
    "MAMMOGRAFIA": {
        'Wnorm': 6.7,
        'Kp1': None, # Solo calcolo secondario per NCRP 147
        'Ksec1_LeakSide': 1.1e-2, # 1.1*10^-2
        'Ksec1_ForBack': 4.9e-2, # 4.9*10^-2
        'Ksec1_Comb': 4.9e-2,
    },
    # 8. ANGIOGRAFIA CARDIACA
    "ANGIO CARDIACA": {
        'Wnorm': 160.0,
        'Kp1': None, # Solo calcolo secondario
        'Ksec1_LeakSide': 2.7,
        'Ksec1_ForBack': 3.7,
        'Ksec1_Comb': 3.8,
    },
    # 9. ANGIOGRAFIA PERIFERICA
    "ANGIO PERIFERICA": {
        'Wnorm': 64.0,
        'Kp1': None, # Solo calcolo secondario
        'Ksec1_LeakSide': 6.6e-1, # 6.6*10^-1
        'Ksec1_ForBack': 9.5e-1, # 9.5*10^-1
        'Ksec1_Comb': 9.5e-1,
    }
}


# Parametri di Fitting (Alfa, Beta, Gamma) per Barriera Primaria (Tabella B.1)
ATTENUATION_DATA_PRIMARY = {
    "STANZA RADIOGRAFICA (TUTTE BARRIERE)": {
        "PIOMBO": {'alpha': 2.346, 'beta': 1.59e+01, 'gamma': 4.982e-01}, 
        "CEMENTO": {'alpha': 3.626e-02, 'beta': 1.429e-01, 'gamma': 4.931e-01}
    },
    "STANZA RADIOGRAFICA (CHEST BUCKY)": {
        "PIOMBO": {'alpha': 2.264, 'beta': 1.308e+01, 'gamma': 5.6e-01},
        "CEMENTO": {'alpha': 3.552e-02, 'beta': 1.177e-01, 'gamma': 6.007e-01}
    },
    "STANZA RADIOGRAFICA (PIANO/ALTRE BARRIERE)": {
        "PIOMBO": {'alpha': 2.651, 'beta': 1.656e+01, 'gamma': 4.585e-01},
        "CEMENTO": {'alpha': 3.994e-02, 'beta': 1.448e-01, 'gamma': 4.231e-01}
    },
    "FLUOROSCOPIA (R&F)": {
        "PIOMBO": {'alpha': 2.347, 'beta': 1.267e+01, 'gamma': 6.149e-01},
        "CEMENTO": {'alpha': 3.616e-02, 'beta': 9.721e-02, 'gamma': 5.186e-01}
    },
    "RADIOGRAFIA (TUBO R&F)": {
        "PIOMBO": {'alpha': 2.295, 'beta': 1.3e+01, 'gamma': 5.573e-01},
        "CEMENTO": {'alpha': 3.549e-02, 'beta': 1.164e-01, 'gamma': 5.774e-01}
    },
    "STANZA RADIOGRAFICA TORACE": {
        "PIOMBO": {'alpha': 2.283, 'beta': 1.074e+01, 'gamma': 6.37e-01},
        "CEMENTO": {'alpha': 3.622e-02, 'beta': 7.766e-02, 'gamma': 5.404e-01}
    },
    "MAMMOGRAFIA": {
        "PIOMBO": {'alpha': 30.6, 'beta': 1.776e+02, 'gamma': 3.308e-01},
        "CEMENTO": {'alpha': 2.577e-01, 'beta': 1.765, 'gamma': 3.644e-01} 
    },
    "ANGIO CARDIACA": {
        "PIOMBO": {'alpha': 2.389, 'beta': 1.426e+01, 'gamma': 5.948e-01},
        "CEMENTO": {'alpha': 3.717e-02, 'beta': 1.087e-01, 'gamma': 4.879e-01} 
    },
    "ANGIO PERIFERICA": {
        "PIOMBO": {'alpha': 2.728, 'beta': 1.852e+01, 'gamma': 4.614e-01},
        "CEMENTO": {'alpha': 4.292e-02, 'beta': 1.538e+02, 'gamma': 4.236e-01}
    }
}


# Parametri di Fitting (Alfa, Beta, Gamma) per Barriera Secondaria (Tabella C.1)
ATTENUATION_DATA_SECONDARY = {
    "STANZA RADIOGRAFICA (TUTTE BARRIERE)": {
        "PIOMBO": {'alpha': 2.298, 'beta': 1.738e+01, 'gamma': 6.193e-01},
        "CEMENTO": {'alpha': 3.610e-02, 'beta': 1.433e-01, 'gamma': 5.600e-01}
    },
    "STANZA RADIOGRAFICA (CHEST BUCKY)": {
        "PIOMBO": {'alpha': 2.256, 'beta': 1.38e+01, 'gamma': 8.837e-01},
        "CEMENTO": {'alpha': 3.56e-02, 'beta': 1.79e-01, 'gamma': 7.705e-01}
    },
    "STANZA RADIOGRAFICA (PIANO/ALTRE BARRIERE)": {
        "PIOMBO": {'alpha': 2.513, 'beta': 1.734e+01, 'gamma': 4.994e-01},
        "CEMENTO": {'alpha': 3.920e-02, 'beta': 1.464e-01, 'gamma': 4.486e-01} 
    },
    "FLUOROSCOPIA (R&F)": {
        "PIOMBO": {'alpha': 2.322, 'beta': 1.291e+01, 'gamma': 7.575e-01},
        "CEMENTO": {'alpha': 3.630e-02, 'beta': 9.360e+02, 'gamma': 5.955e-01}
    },
    "RADIOGRAFIA (TUBO R&F)": {
        "PIOMBO": {'alpha': 2.272, 'beta': 1.360e+01, 'gamma': 7.184e-01},
        "CEMENTO": {'alpha': 3.560e-02, 'beta': 1.114e-01, 'gamma': 6.620e-01}
    },
    "STANZA RADIOGRAFICA TORACE": {
        "PIOMBO": {'alpha': 2.288, 'beta': 9.848, 'gamma': 1.054},
        "CEMENTO": {'alpha': 3.640e-02, 'beta': 6.590e-02, 'gamma': 7.543e-01}
    },
    "MAMMOGRAFIA": {
        "PIOMBO": {'alpha': 29.91, 'beta': 1.844e+02, 'gamma': 3.550e-01},
        "CEMENTO": {'alpha': 2.539e-01, 'beta': 1.8411, 'gamma': 3.924e-01}
    },
    "ANGIO CARDIACA": {
        "PIOMBO": {'alpha': 2.354, 'beta': 1.494e+01, 'gamma': 7.481e-01},
        "CEMENTO": {'alpha': 3.710e-02, 'beta': 1.067e-01, 'gamma': 5.733e-01}
    },
    "ANGIO PERIFERICA": {
        "PIOMBO": {'alpha': 2.661, 'beta': 1.954e+01, 'gamma': 5.094e-01},
        "CEMENTO": {'alpha': 4.219e-02, 'beta': 1.559e-01, 'gamma': 4.472e-01}
    }
}


# NUOVI DIZIONARI PER TC (RAMO 3) - Basati su kVp
# TABELLA A.1 (Piombo) (Cemento) e equazione A.2 NCRP 147
ATTENUATION_DATA_TC = {
    "PIOMBO": {
        "120 kVp": {'alpha': 2.246, 'beta': 8.95, 'gamma': 5.873e-01},
        "140 kVp": {'alpha': 2.009, 'beta': 5.916, 'gamma':4.018e-01}
    },
    "CEMENTO": {
        "120 kVp": {'alpha': 3.566e-02, 'beta': 7.109e-02, 'gamma': 6.073e-01},
        "140 kVp": {'alpha': 3.345e-02, 'beta': 7.476e-02, 'gamma': 1.047}
    }
}


# NUOVO DIZIONARIO PER LE SCELTE DELL'UTENTE (PRESHIELDING_XPRE_OPTIONS)
# Spessore di Preshielding (Xpre) in mm (Tabella 4.6 - NCRP 147)
PRESHIELDING_XPRE_OPTIONS = {
    # Image receptor in table/holder attenuation by grid and cassette and image receptor
    "NESSUNO (0.0 mm) - Table/Holder": 0.0,
    "PIOMBO (0.85 mm) - Table/Holder": 0.85,
    "CEMENTO (72.0 mm) - Table/Holder": 72.0,
    "ACCIAIO (7.0 mm) - Table/Holder": 7.0,

    # Cross-table lateral attenuation by grid and cassette only
    "NESSUNO (0.0 mm) - Cross-Table Lateral": 0.0,
    "PIOMBO (0.3 mm) - Cross-Table Lateral": 0.3,
    "CEMENTO (30.0 mm) - Cross-Table Lateral": 30.0,
    "ACCIAIO (2.0 mm) - Cross-Table Lateral": 2.0
}

# Mapping delle opzioni X_PRE per la logica dinamica
X_PRE_TABLE_HOLDER_KEYS = [k for k in PRESHIELDING_XPRE_OPTIONS.keys() if "Table/Holder" in k]
X_PRE_CROSS_TABLE_KEYS = [k for k in PRESHIELDING_XPRE_OPTIONS.keys() if "Cross-Table Lateral" in k]


# DLP Fissi di Riferimento per il calcolo K1sec (Tabella 5.2 NCRP 147)
# DLP [mGy*cm]
DLP_TC_FIXED_VALUES = {
    "HEAD": 1200, 
    "BODY": 550, 
}


# Coefficienti di Kerma per TC (Tabella 5.2, parte inferiore)
# Coefficiente di Kerma di diffusione per testa (cm^-1)
K_HEAD_DIFF = 9.0e-5 # 9 x 10^-5 cm^-1
# Coefficiente di Kerma di diffusione per corpo (cm^-1)
K_BODY_DIFF = 3.0e-4 # 3 x 10^-4 cm^-1


# TABELLE DI ATTENUAZIONE NCRP 147 PER RAMO 4
# Valori di spessore X (mm Pb o mm Cemento) in funzione di n_TVL (indice da 0 a 26)
NCRP_TABLES = {
    # STANZA RADIOGRAFICA - PIOMBO
    '4.5a': { # Primaria, No preshielding
        'chest buck wall': np.array([1.05, 1.3, 1.45, 1.6, 1.68, 1.75, 1.8, 1.85, 1.9, 1.95, 2.0, 2.03, 2.06, 2.09, 2.12, 2.13, 2.17, 2.19, 2.21, 2.23, 2.25, 2.28, 2.3, 2.32, 2.34, 2.35, 2.37]),
        'floor': np.array([0.92, 1.13, 1.24, 1.37, 1.42, 1.5, 1.55, 1.6, 1.62, 1.65, 1.68, 1.71, 1.73, 1.77, 1.8, 1.81, 1.82, 1.85, 1.87, 1.9, 1.92, 1.92, 1.93, 1.96, 1.98, 1.99, 2.0]),
        'cross-table lateral wall': np.array([0.5, 0.61, 0.77, 0.81, 0.84, 0.92, 0.97, 1.01, 1.05, 1.1, 1.11, 1.13, 1.16, 1.19, 1.21, 1.23, 1.24, 1.26, 1.28, 1.3, 1.31, 1.32, 1.33, 1.34, 1.36, 1.37, 1.38]),
        'wall opposite chest bucky': np.array([0.2, 0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.61, 0.65, 0.68, 0.7, 0.72, 0.74, 0.78, 0.8, 0.8, 0.81, 0.83, 0.85, 0.87, 0.89, 0.9, 0.91, 0.92, 0.94, 0.95, 0.96])
    }, 
    '4.5b': { # Primaria, Si preshielding
        'chest buck wall': np.array([0.25, 0.5, 0.63, 0.74, 0.82, 0.9, 0.97, 1.01, 1.04, 1.11, 1.15, 1.2, 1.21, 1.23, 1.26, 1.3, 1.32, 1.35, 1.37, 1.4, 1.41, 1.43, 1.46, 1.48, 1.5, 1.51, 1.52]),
        'floor': np.array([0.13, 0.3, 0.4, 0.5, 0.58, 0.61, 0.68, 0.71, 0.75, 0.79, 0.81, 0.83, 0.86, 0.9, 0.92, 0.94, 0.97, 0.98, 1.0, 1.02, 1.04, 1.06, 1.08, 1.09, 1.1, 1.11, 1.12]),
        'cross-table lateral wall': np.array([0.3, 0.44, 0.57, 0.62, 0.7, 0.73, 0.8, 0.82, 0.85, 0.9, 0.92, 0.95, 0.97, 1.0, 1.02, 1.04, 1.06, 1.08, 1.09, 1.1, 1.12, 1.13, 1.14, 1.15, 1.17, 1.18, 1.19]),
        'wall opposite chest bucky': np.array([0.1, 0.2, 0.25, 0.3, 0.35, 0.4, 0.42, 0.46, 0.5, 0.54, 0.57, 0.58, 0.6, 0.61, 0.63, 0.66, 0.68, 0.7, 0.71, 0.72, 0.73, 0.75, 0.77, 0.78, 0.8, 0.81, 0.82])
    }, 
    '4.5c': { # Secondaria (usa 'floor' come rappresentante, i dettagli utente non coprono tutte le chiavi secondarie)
        'floor': np.array([0.1, 0.15, 0.2, 0.25, 0.3, 0.32, 0.35, 0.38, 0.4, 0.42, 0.45, 0.47, 0.5, 0.51, 0.52, 0.54, 0.55, 0.56, 0.57, 0.6, 0.61, 0.62, 0.64, 0.65, 0.66, 0.67, 0.68])
    },

    # STANZA RADIOGRAFICA - CEMENTO
    '4.6a': { # Primaria, No preshielding
        'chest buck wall': np.array([90, 105, 116, 125, 130, 135, 140, 145, 148, 150, 153, 155, 157, 160, 161, 162, 164, 166, 168, 170, 171, 172, 174, 175, 176, 177, 178]),
        'floor': np.array([75, 90, 100, 105, 110, 115, 118, 122, 125, 126, 128, 130, 132, 134, 136, 137, 138, 140, 141, 142, 144, 145, 146, 147, 148, 149, 150]),
        'cross-table lateral wall': np.array([40, 53, 60, 65, 70, 75, 78, 80, 83, 85, 87, 88, 90, 92, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 105, 106, 107]),
        'wall opposite chest bucky': np.array([20, 30, 35, 40, 44, 46, 50, 51, 54, 55, 57, 59, 60, 61, 63, 65, 66, 67, 68, 70, 71, 72, 73, 74, 75, 76, 77])
    }, 
    '4.6b': { # Primaria, Si preshielding
        'chest buck wall': np.array([22, 35, 46, 55, 60, 65, 70, 73, 76, 80, 81, 84, 86, 88, 90, 91, 93, 94, 95, 97, 98, 100, 101, 103, 104, 105, 106]),
        'cross-table lateral wall': np.array([20, 35, 43, 48, 53, 56, 60, 63, 65, 67, 70, 71, 73, 75, 76, 77, 78, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89]),
        'floor': np.array([10, 30, 32, 38, 42, 47, 50, 54, 56, 58, 60, 62, 65, 66, 68, 70, 71, 72, 74, 75, 76, 77, 78, 79, 80, 81, 82]),
        'wall opposite chest bucky': np.array([9, 16, 22, 26, 30, 36, 38, 40, 42, 43, 45, 47, 49, 50, 51, 52, 53, 55, 56, 57, 58, 59, 60, 61, 62, 63])
    }, 
    '4.6c': { # Secondaria
        'floor': np.array([8, 15, 20, 25, 27, 30, 32, 34, 36, 37, 40, 41, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57]) 
    },

    # R&F - PIOMBO
    '4.7a': { # Primaria, No preshielding
        'floor': np.array([1.2, 1.4, 1.55, 1.62, 1.68, 1.8, 1.84, 1.86, 1.91, 2.0, 2.02, 2.04, 2.1, 2.13, 2.18, 2.2, 2.22, 2.23, 2.27, 2.3, 2.31, 2.33, 2.36, 2.38, 2.4, 2.41, 2.42]),
        'chest buck wall': np.array([1, 1.2, 1.4, 1.5, 1.6, 1.64, 1.72, 1.8, 1.83, 1.9, 1.92, 1.95, 2, 2.01, 2.04, 2.08, 2.10, 2.12, 2.17, 2.18, 2.2, 2.21, 2.22, 2.23, 2.24, 2.25, 2.26]), 
        'cross-table lateral wall': np.array([0.6, 0.8, 0.9, 1, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.41, 1.46, 1.5, 1.56, 1.57, 1.58, 1.6, 1.61, 1.65, 1.67, 1.7, 1.72, 1.73, 1.75, 1.76, 1.77]),
        'wall opposite chest bucky': np.array([0.35, 0.5, 0.6, 0.7, 0.8, 0.83, 0.9, 0.95, 1, 1.03, 1.07, 1.1, 1.15, 1.17, 1.2, 1.21, 1.23, 1.27, 1.3, 1.32, 1.34, 1.36, 1.37, 1.38, 1.4, 1.41, 1.42])
    }, 
    '4.7b': { # Primaria, Si preshielding
        'floor': np.array([0.7, 0.9, 1.1, 1.2, 1.25, 1.35, 1.4, 1.43, 1.5, 1.52, 1.57, 1.6, 1.63, 1.67, 1.7, 1.72, 1.75, 1.79, 1.81, 1.82, 1.84, 1.87, 1.89, 1.9, 1.91, 1.92, 1.93]),
        'cross-table lateral wall': np.array([0.52, 0.78, 0.9, 0.98, 1.02, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.42, 1.45, 1.49, 1.52, 1.54, 1.57, 1.6, 1.61, 1.62, 1.64, 1.66, 1.7, 1.71, 1.72, 1.73]),
        'chest buck wall': np.array([0.42, 0.6, 0.8, 0.9, 1, 1.05, 1.11, 1.2, 1.23, 1.29, 1.31, 1.35, 1.38, 1.4, 1.42, 1.45, 1.47, 1.51, 1.54, 1.57, 1.58, 1.59, 1.6, 1.62, 1.65, 1.66, 1.67]),
        'wall opposite chest bucky': np.array([0.3, 0.5, 0.6, 0.7, 0.78, 0.81, 0.88, 0.91, 0.98, 1.02, 1.03, 1.1, 1.13, 1.15, 1.18, 1.2, 1.22, 1.25, 1.28, 1.3, 1.31, 1.33, 1.35, 1.37, 1.39, 1.4, 1.41])
    }, 
    '4.7c': { # Secondaria
        'floor': np.array([0.3, 0.56, 0.7, 0.8, 0.9, 0.95, 1, 1.06, 1.1, 1.15, 1.2, 1.22, 1.25, 1.28, 1.3, 1.32, 1.35, 1.38, 1.4, 1.41, 1.43, 1.45, 1.47, 1.49, 1.51, 1.52, 1.53])
    },

    # R&F - CEMENTO
    '4.8a': { # Primaria, No preshielding
        'floor': np.array([90, 107, 120, 125, 131, 138, 140, 143, 147, 150, 152, 155, 157, 159, 161, 163, 165, 166, 168, 169, 170, 171, 172, 173, 174, 175, 176]), 
        'chest buck wall': np.array([90, 100, 110, 118, 122, 130, 133, 138, 141, 144, 147, 150, 151, 153, 156, 157, 159, 160, 161, 163, 165, 167, 168, 169, 170, 171, 172]),
        'cross-table lateral wall': np.array([50, 62, 71, 79, 81, 83, 90, 92, 96, 100, 102, 104, 106, 108, 110, 111, 113, 116, 118, 119, 120, 121, 122, 123, 124, 125, 126]),
        'wall opposite chest bucky': np.array([30, 42, 51, 58, 61, 66, 70, 72, 77, 80, 81, 83, 85, 87, 90, 91, 93, 95, 97, 98, 99, 100, 101, 102, 103, 104, 105])
    }, 
    '4.8b': { # Primaria, Si preshielding
        'floor': np.array([50, 65, 75, 84, 90, 95, 98, 98, 101, 105, 107, 110, 112, 114, 116, 118, 120, 122, 124, 125, 125, 126, 127, 128, 130, 131, 132]), 
        'cross-table lateral wall': np.array([45, 60, 67, 73, 78, 81, 85, 88, 91, 95, 97, 100, 102, 105, 107, 108, 110, 111, 113, 115, 116, 117, 118, 119, 120, 121, 122]),
        'chest buck wall': np.array([35, 50, 60, 65, 71, 76, 81, 85, 88, 91, 93, 96, 98, 100, 101, 103, 105, 106, 108, 110, 111, 112, 113, 115, 116, 117, 118]),
        'wall opposite chest bucky': np.array([30, 40, 50, 60, 63, 67, 70, 73, 76, 79, 81, 83, 85, 86, 87, 90, 91, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102])
    }, 
    '4.8c': { # Secondaria
        'floor': np.array([30, 46, 50, 61, 66, 71, 75, 78, 80, 84, 85, 87, 90, 92, 94, 95, 96, 98, 100, 101, 102, 103, 104, 105, 106, 107, 108]), 
    }
}


# ====================================================================
# 2. FUNZIONI ANALITICHE BASE
# ====================================================================


def calcola_spessore_x(alpha, beta, gamma, B):
    """
    Calcola lo spessore x richiesto data la trasmittanza B (formula inversa NCRP 147).
    """
    try:
        if B is None or B <= 0 or alpha == 0 or gamma == 0:
            return 999.0
        
        # Formula: X = (1 / (alpha * gamma)) * ln( [ B^(-gamma) + (beta / alpha) ] / [ 1 + (beta / alpha) ] )
        
        numeratore_ln = B**(-gamma) + (beta / alpha)
        denominatore_ln = 1 + (beta / alpha)
        
        if denominatore_ln == 0 or numeratore_ln <= 0:
            return 999.0
            
        x = (1 / (alpha * gamma)) * math.log(numeratore_ln / denominatore_ln)
        return max(0.0, x)
        
    except Exception:
        return 999.0


def calcola_kerma_incidente(K_val, U, N, d):
    """
    Calcola il kerma in aria non schermato alla distanza d per unità di tempo.
    Formula: kerma_non_schermato = K_val * U * N / d^2 
    """
    try:
        if d <= 0: return 0.0
        # Utilizziamo la formula generica NCRP 147: $K_{tu} \approx (K_{val} \cdot U \cdot N) / d^2$
        kerma = (K_val * U * N) / (d ** 2)
        return kerma
    except Exception:
        return 0.0


# ====================================================================
# 3. FUNZIONI DI CALCOLO SPECIFICHE (RAMO 1, 2, 3, 4)
# ====================================================================


def calculate_primary_thickness(params):
    """ Implementa il calcolo Primario (Ramo 1). """
    P = params.get('P_mSv_wk', 0.0) 
    T = params.get('tasso_occupazione_T', 1.0)
    d = params.get('distanza_d', 2.0)
    U = params.get('fattore_uso_U', 0.25)
    N = params.get('pazienti_settimana_N', 100)
    modalita = params.get('modalita_radiografia')
    materiale = params.get('materiale_schermatura')
    Xpre = params.get('X_PRE_mm', 0.0) 

    # Mappaggio della modalità
    modalita_map = {
        "STANZA RADIOGRAFICA": "STANZA RADIOGRAFICA (PIANO/ALTRE BARRIERE)", # Default per primario generico con Kp1
        "FLUOROSCOPIA": "FLUOROSCOPIA (R&F)", 
        "RADIOGRAFIA TORACE": "STANZA RADIOGRAFICA TORACE",
        "R&F": "FLUOROSCOPIA (R&F)", # Assumiamo fluoro
    }
    modalita_key = modalita_map.get(modalita, modalita) # Usa la chiave mappata o l'input

    Kp1_data = KERMA_DATA.get(modalita_key, {}).get('Kp1')
    if Kp1_data is None:
        return 0.0, 0.0, f"Dati Kp1 non definiti per la modalità '{modalita_key}' e barriera Primaria."

    
    if modalita_key not in ATTENUATION_DATA_PRIMARY or materiale not in ATTENUATION_DATA_PRIMARY[modalita_key]:
        return 0.0, 0.0, f"Dati di attenuazione Primaria mancanti per '{modalita_key}'."
        
    data = ATTENUATION_DATA_PRIMARY[modalita_key][materiale]
    alpha, beta, gamma = data['alpha'], data['beta'], data['gamma']
    
    kerma_non_schermato_mGy_wk = calcola_kerma_incidente(Kp1_data, U, N, d) # Kp1 in mGy*m^2 / mAs
    
    if kerma_non_schermato_mGy_wk * T == 0 or P == 0:
        return 0.0, 0.0, "Kerma o Tasso di Occupazione (T) o Dose Limite (P) nullo/i."
        
    B_P = P / (kerma_non_schermato_mGy_wk * T)
    
    Xref_mm = calcola_spessore_x(alpha, beta, gamma, B_P)
    Xfinale_mm = max(0.0, Xref_mm - Xpre)
    
    log_msg = f"Kp1={Kp1_data:.2f}. B={B_P:.4e}. Xref={Xref_mm:.2f}mm. Xpre={Xpre:.2f}mm. Modalità NCRP: {modalita_key}"
    return Xfinale_mm, kerma_non_schermato_mGy_wk, log_msg


def calculate_secondary_thickness(params):
    """ Implementa il calcolo Secondario (Ramo 1/2). """
    P = params.get('P_mSv_wk', 0.0) 
    T = params.get('tasso_occupazione_T', 1.0)
    d = params.get('distanza_d', 2.0)
    U = 1.0 # U è tipicamente 1.0 per la secondaria (NCRP 147 Eq. 4.4)
    N = params.get('pazienti_settimana_N', 100)
    modalita = params.get('modalita_radiografia')
    materiale = params.get('materiale_schermatura')
    Xpre = params.get('X_PRE_mm', 0.0) 

    # Mappaggio della modalità radiografica alla chiave dati NCRP 147
    modalita_map = {
        "STANZA RADIOGRAFICA": "STANZA RADIOGRAFICA (TUTTE BARRIERE)",
        "RADIOGRAFIA TORACE": "STANZA RADIOGRAFICA TORACE",
        "FLUOROSCOPIA": "FLUOROSCOPIA (R&F)", 
        "R&F": "RADIOGRAFIA (TUBO R&F)", # Usiamo il tubo radiogeno R&F per secondaria generica in R&F
        "MAMMOGRAFIA": "MAMMOGRAFIA",
        "ANGIO CARDIACA": "ANGIO CARDIACA",
        "ANGIO PERIFERICA": "ANGIO PERIFERICA",
        "ANGIO NEURO": "ANGIO PERIFERICA" 
    }
    
    modalita_key = modalita_map.get(modalita)
    if not modalita_key:
        return 0.0, 0.0, 0.0, 0.0, f"Modalità '{modalita}' non mappata per il calcolo Secondario."

    Ksec1_data = KERMA_DATA.get(modalita_key, {}).get('Ksec1_Comb')
    if Ksec1_data is None:
        return 0.0, 0.0, 0.0, 0.0, f"Dati Ksec1_Comb non definiti per la modalità '{modalita_key}'."

    
    if modalita_key not in ATTENUATION_DATA_SECONDARY or materiale not in ATTENUATION_DATA_SECONDARY[modalita_key]:
        return 0.0, 0.0, 0.0, 0.0, f"Dati di attenuazione Secondaria mancanti per '{modalita_key}'."
        
    data = ATTENUATION_DATA_SECONDARY[modalita_key][materiale]
    alpha, beta, gamma = data['alpha'], data['beta'], data['gamma']
    
    kerma_non_schermato_mGy_wk = calcola_kerma_incidente(Ksec1_data, U, N, d)
    
    if kerma_non_schermato_mGy_wk * T == 0 or P == 0:
        return 0.0, 0.0, 0.0, 0.0, "Kerma o Tasso di Occupazione (T) o Dose Limite (P) nullo/i."
        
    B_S = P / (kerma_non_schermato_mGy_wk * T)
    
    Xref_mm = calcola_spessore_x(alpha, beta, gamma, B_S)
    Xfinale_mm = max(0.0, Xref_mm - Xpre)
    
    log_msg = f"Ksec1={Ksec1_data:.4e}. B={B_S:.4e}. Xref={Xref_mm:.2f}mm. Xpre={Xpre:.2f}mm. (Modello combinato Ksec1, Modalità NCRP: {modalita_key})"
    
    return Xfinale_mm, Xfinale_mm, Xfinale_mm, kerma_non_schermato_mGy_wk, log_msg # X_L=X_S=X_finale


def calculate_special_secondary_thickness(params):
    """ Implementa il calcolo Secondario Specializzato (Ramo 2). Stesso flusso logico di Ramo 1/Secondario. """
    return calculate_secondary_thickness(params)


def calculate_tc_thickness(params):
    """ 
    Implementa il calcolo Secondario (Ramo 3 - TC).
    Utilizza i DLP fissi (1200 mGy*cm per Head, 550 mGy*cm per Body) per calcolare il Kerma K1sec.
    """
    P = params.get('P_mSv_wk', 0.0) 
    T = params.get('tasso_occupazione_T', 1.0)
    d = params.get('distanza_d', 2.0) # $d$ in metri
    materiale = params.get('materiale_schermatura')
    Xpre = params.get('X_PRE_mm', 0.0)
    
    N_head = params.get('weekly_n_head', 0) 
    N_body = params.get('weekly_n_body', 0)
    Kc = params.get('contrast_factor', 1.0)
    kvp = params.get('kvp_tc')
    
    # 1. Calcolo del Kerma non schermato a 1m per paziente (K1sec)
    dlp_head = DLP_TC_FIXED_VALUES["HEAD"]
    K1sec_head_mGy_paz = K_HEAD_DIFF * dlp_head * Kc # [cm^-1] * [mGy*cm] * [] = [mGy]
    
    dlp_body = DLP_TC_FIXED_VALUES["BODY"]
    K1sec_body_mGy_paz = 1.2 * K_BODY_DIFF * dlp_body * Kc 
    
    # 2. Calcolo del Kerma non schermato totale settimanale alla distanza d ($K_{tu}$)
    total_kerma_at_1m_mGy_wk = (K1sec_head_mGy_paz * N_head) + (K1sec_body_mGy_paz * N_body)
    
    if d <= 0:
        kerma_tc_non_schermato_mGy_wk = 0.0
    else:
        kerma_tc_non_schermato_mGy_wk = (1 / (d ** 2)) * total_kerma_at_1m_mGy_wk
    
    # 3. Calcolo del Fattore di Trasmittanza B ($B_{T}$)
    if kerma_tc_non_schermato_mGy_wk * T <= 0 or P == 0:
        B_T = 1.0 
    else:
        B_T = P / (T * kerma_tc_non_schermato_mGy_wk)
        
    # 4. Calcolo dello Spessore X richiesto
    
    if materiale not in ATTENUATION_DATA_TC or kvp not in ATTENUATION_DATA_TC[materiale]:
        return 0.0, 0.0, f"Dati di attenuazione TC (Materiale/kVp) mancanti per {materiale} a {kvp}.", 0.0, 0.0


    data_tc_attenuation = ATTENUATION_DATA_TC[materiale][kvp]
    alpha, beta, gamma = data_tc_attenuation['alpha'], data_tc_attenuation['beta'], data_tc_attenuation['gamma']
    
    Xref_mm = calcola_spessore_x(alpha, beta, gamma, B_T)
    Xfinale_mm = max(0.0, Xref_mm - Xpre)


    log_msg = (
        f"K1sec(Head) = {K1sec_head_mGy_paz:.2e} mGy/paz. "
        f"K1sec(Body) = {K1sec_body_mGy_paz:.2e} mGy/paz. "
        f"$K_{{tu}}$ (a d={d}m) = {kerma_tc_non_schermato_mGy_wk:.2e} mGy/wk. "
        f"B = {B_T:.4e}. Xref={Xref_mm:.2f}mm. Xpre={Xpre:.2f}mm."
    )
    
    return Xfinale_mm, kerma_tc_non_schermato_mGy_wk, log_msg, K1sec_head_mGy_paz, K1sec_body_mGy_paz


def ramo4_calc(N, T, P_usv, d, modalita, materiale, preshielding, dettaglio):
    """
    Calcola lo spessore di schermatura (X) per il Ramo 4 (NCRP 147, Tabelle 4.x) tramite interpolazione.
    """
    
    # 1. Conversione Unità e Calcolo Fattore di Attenuazione Logaritmico (n_TVL)
    P_mgy = P_usv * 1e-3 # P in mGy/wk (da µSv/wk, assumendo 1 µSv ~ 1 µGy)
    d2 = d ** 2

    # Kerma a 1m per raggi X diagnostici (NCRP 147, 100 kVp)
    # K_P = 0.011 mGy / (mAs * m^2) per barriera primaria (come specificato nella descrizione RAMO 4)
    K_P = 0.011 
    
    # Calcolo del reciproco dell'attenuazione richiesta, B^-1
    # B^-1 = (N * T * K_P) / (P * d^2)
    try:
        B_inv = (N * T * K_P) / (P_mgy * d2)
        n_TVL = math.log10(B_inv)
    except ZeroDivisionError:
        return 0.0, 0.0, "Errore: Divisione per zero (P o d nullo).", "N/A"
    except ValueError: # math.log10(x) where x <= 0
        return 0.0, 0.0, "Errore: Calcolo logaritmico non valido (B⁻¹ <= 0).", "N/A"

    # 2. Selezione della Tabella
    modalita_map = {
        'Stanza Radiografica': '4.5' if materiale == 'PIOMBO' else '4.6',
        'R&F': '4.7' if materiale == 'PIOMBO' else '4.8'
    }
    table_prefix = modalita_map.get(modalita)

    if not table_prefix:
        return 0.0, 0.0, "Errore: Modalità radiografica RAMO 4 non valida.", "N/A"

    # Seleziona la variante a/b (Primaria) o c (Secondaria)
    if dettaglio in ['chest buck wall', 'cross-table lateral wall', 'floor', 'wall opposite chest bucky'] and dettaglio != 'floor':
        # Primaria (usa preshielding SI/NO)
        table_suffix = 'a' if preshielding == 'NO' else 'b'
        table_key = table_prefix + table_suffix
        dettaglio_key = dettaglio
    else:
        # Secondaria (forzata a 'floor' per usare la tabella 'c')
        table_key = table_prefix + 'c'
        dettaglio_key = 'floor' # Usiamo 'floor' che è presente in tutte le tabelle secondarie X.xc

    # 3. Interpolazione
    if table_key not in NCRP_TABLES or dettaglio_key not in NCRP_TABLES[table_key]:
        return 0.0, 0.0, f"Errore: Combinazione di parametri non valida. Tabella: {table_key}, Dettaglio: {dettaglio_key}", "N/A"

    X_data = NCRP_TABLES[table_key][dettaglio_key]
    n_values = np.arange(len(X_data)) # n_TVL da 0 a 26

    # Limita/Estrapola l'interpolazione
    if n_TVL < n_values.min():
        X = 0.0
    elif n_TVL > n_values.max():
        # Estrapolazione lineare con l'ultimo TVL
        TVL_ultimo = X_data[-1] - X_data[-2]
        X = X_data[-1] + (n_TVL - n_values.max()) * TVL_ultimo
    else:
        # Interpolazione lineare
        f = interp1d(n_values, X_data, kind='linear')
        X = f(n_TVL).item()

    unita = "mm Piombo (Pb)" if materiale == 'PIOMBO' else "mm Cemento"
    log_msg = f"n_TVL={n_TVL:.2f}. B_inv={B_inv:.4e}. Tabella NCRP: {table_key}. Dettaglio: {dettaglio_key}. Unità: {unita}"
    return X, n_TVL, log_msg, unita


# ====================================================================
# 4. LOGICA DI BACKEND PRINCIPALE (IF/THEN/ELSE)
# ====================================================================


def run_shielding_calculation(params):
    """
    Funzione principale che gestisce la logica if-then-else e indirizza i calcoli.
    """
    tipo_immagine = params.get('tipo_immagine')
    tipo_barriera = params.get('tipo_barriera')
    modalita_radiografia = params.get('modalita_radiografia')
    
    risultati = {'ramo_logico': 'Non Eseguito', 'spessore_finale_mm': 0.0}
    
    # -------------------------------------------------------------------------
    # RAMO 1 & 2: DIAGNOSTICA STANDARD/SPECIALIZZATA (Attenuazione per FITTING)
    # -------------------------------------------------------------------------
    if tipo_immagine == "RADIOLOGIA DIAGNOSTICA":
        
        # Ramo 2: Diagnostica Specializzata (Solo secondaria)
        if modalita_radiografia in ["MAMMOGRAFIA", "ANGIO CARDIACA", "ANGIO PERIFERICA", "ANGIO NEURO"]:
            risultati['ramo_logico'] = "RAMO 2: DIAGNOSTICA SPECIALIZZATA"
            if tipo_barriera == "PRIMARIA":
                risultati['spessore_finale_mm'] = 0.0
                risultati['dettaglio'] = "Calcolo Primario omesso (già gestito da detettore/apparecchio)."
            elif tipo_barriera == "SECONDARIA":
                X_mm, X_L, X_S, K_non_schermato, log_msg = calculate_special_secondary_thickness(params)
                risultati.update({'spessore_finale_mm': X_mm, 'X_fuga_mm': X_L, 'X_diffusione_mm': X_S, 'kerma_non_schermato': K_non_schermato, 'dettaglio': f"Eseguito calcolo Secondario Specializzato. {log_msg}"})
        
        # Ramo 1: Diagnostica Standard (Primaria e Secondaria)
        elif modalita_radiografia in ["STANZA RADIOGRAFICA", "RADIOGRAFIA TORACE", "FLUOROSCOPIA", "R&F"]:
             risultati['ramo_logico'] = "RAMO 1: DIAGNOSTICA STANDARD"
             if tipo_barriera == "PRIMARIA":
                 X_mm, K_non_schermato, log_msg = calculate_primary_thickness(params) 
                 risultati.update({'spessore_finale_mm': X_mm, 'kerma_non_schermato': K_non_schermato, 'dettaglio': f"Eseguito calcolo Primario. {log_msg}"})
             elif tipo_barriera == "SECONDARIA":
                 X_mm, X_L, X_S, K_non_schermato, log_msg = calculate_secondary_thickness(params)
                 risultati.update({'spessore_finale_mm': X_mm, 'X_fuga_mm': X_L, 'X_diffusione_mm': X_S, 'kerma_non_schermato': K_non_schermato, 'dettaglio': f"Eseguito calcolo Secondario. {log_msg}"})
             else:
                 risultati['errore'] = "Tipo di barriera non specificato per il Ramo 1."
        
        else:
            risultati['errore'] = "Modalità Radiografica non riconosciuta nel Ramo 1/2."


    # -------------------------------------------------------------------------
    # RAMO 3: TC (Tomografia Computerizzata)
    # -------------------------------------------------------------------------
    elif tipo_immagine == "TC": 
        risultati['ramo_logico'] = 'RAMO 3: TC (Calcolo Spessore)'
        if tipo_barriera == "PRIMARIA":
            risultati['spessore_finale_mm'] = 0.0
            risultati['kerma_non_schermato'] = 0.0
            risultati['dettaglio'] = "TC - Calcolo Primario non richiesto."
        elif tipo_barriera == "SECONDARIA":
            X_mm, K_tu, log_msg, K1sec_head, K1sec_body = calculate_tc_thickness(params)
            risultati.update({
                'spessore_finale_mm': X_mm, 'kerma_non_schermato': K_tu, 
                'dettaglio': f"Spessore TC calcolato. {log_msg}",
                'K1sec_head_mGy_paz': K1sec_head, 'K1sec_body_mGy_paz': K1sec_body
            })
        else:
            risultati['errore'] = "Tipo di barriera non specificato nel Ramo 3 (TC)."
    
    # -------------------------------------------------------------------------
    # RAMO 4: INTERPOLAZIONE TABELLE NCRP 147 (NUOVO)
    # -------------------------------------------------------------------------
    elif tipo_immagine == "RAMO 4: INTERPOLAZIONE TABELLE":
        risultati['ramo_logico'] = 'RAMO 4: INTERPOLAZIONE TABELLE (NCRP 147)'

        N_input = params.get('N_mAs_wk', 0.0)
        T_input = params.get('tasso_occupazione_T', 1.0)
        P_input = params.get('P_mSv_wk', 0.0) * 1000.0 # Converti mSv/wk in µSv/wk
        d_input = params.get('distanza_d', 2.0)
        modalita_ramo4 = params.get('modalita_radiografia_ramo4')
        preshielding = params.get('preshielding')
        dettaglio_barriera = params.get('dettaglio_barriera')
        materiale = params.get('materiale_schermatura')
        
        if N_input <= 0 or P_input <= 0 or d_input <= 0:
            risultati['errore'] = "Assicurati che N, P, e d siano maggiori di zero per il calcolo RAMO 4."
            return risultati
            
        try:
            X_mm, n_TVL_calc, log_msg, unita = ramo4_calc(
                N_input, T_input, P_input, d_input,
                modalita_ramo4, materiale, preshielding, dettaglio_barriera
            )

            if "Errore" in log_msg:
                 risultati['errore'] = log_msg
            else:
                risultati.update({
                    'spessore_finale_mm': X_mm,
                    'n_TVL_calc': n_TVL_calc,
                    'unita_misura': unita,
                    'dettaglio': f"Spessore RAMO 4 calcolato. {log_msg}",
                })
        except Exception as e:
            risultati['errore'] = f"Errore non gestito nel calcolo RAMO 4: {e}"
            
    
    else:
        risultati['errore'] = "Combinazione Tipo Immagine/Modalità non riconosciuta."
        
    return risultati


# ====================================================================
# 5. INTERFACCIA UTENTE STREAMLIT
# ====================================================================


def main_app():
    st.set_page_config(page_title="Calcolo Schermatura NCRP 147", layout="wide")
    st.title("🛡️ Calcolo Schermatura Radiologica (NCRP 147)")
    st.caption("Implementazione della logica Ramo 1, 2, 3 (TC) e Ramo 4 (Interpolazione).")
    
    # Variabili da inizializzare per RAMO 4 (nuove)
    modalita_radiografia_ramo4 = None
    dettaglio_barriera = None
    preshielding = None
    N_input_ramo4 = None
    
    # Inizializzazione per risolvere l'errore di ambito nella sezione Output
    # Usiamo la variabile di input che è sempre definita
    tasso_occupazione_T = 1.0 # <--- INIZIALIZZAZIONE AGGIUNTA
    P_mSv_wk = 0.02 # <--- INIZIALIZZAZIONE AGGIUNTA
    distanza_d = 2.0 # <--- INIZIALIZZAZIONE AGGIUNTA
    X_PRE_selection_key = "N/A" # <--- INIZIALIZZAZIONE AGGIUNTA
    
    # Variabili da inizializzare per RAMO 3 (TC)
    weekly_n_head = 0
    weekly_n_body = 0
    contrast_factor = 1.0
    
    # --- Sezione Input ---
    col1, col2, col3 = st.columns(3)
    
    # COL 1: Input Logici
    with col1:
        st.header("1. Selezione informazioni principali")
        
        tipo_immagine = st.selectbox("Tipo di Immagine", 
                                     ["RADIOLOGIA DIAGNOSTICA", "TC", "RAMO 4: INTERPOLAZIONE TABELLE"], 
                                     index=0)
        
        # LOGICA PER RAMO 1/2
        if tipo_immagine == "RADIOLOGIA DIAGNOSTICA":
            modalita_radiografia_options = ["STANZA RADIOGRAFICA", "RADIOGRAFIA TORACE", "FLUOROSCOPIA", 
                                             "MAMMOGRAFIA", "ANGIO CARDIACA", "ANGIO PERIFERICA", "ANGIO NEURO", "R&F"]
            modalita_radiografia = st.selectbox("Modalità Radiografica", modalita_radiografia_options, index=0)
            tipo_barriera = st.selectbox("Tipo di Barriera", ["PRIMARIA", "SECONDARIA"])
            
        # LOGICA PER RAMO 3 (TC)
        elif tipo_immagine == "TC":
            modalita_radiografia = "DLP" # Key per RAMO 3
            tipo_barriera = st.selectbox("Tipo di Barriera", ["PRIMARIA", "SECONDARIA"], index=1) 
            
        # LOGICA PER RAMO 4
        else: # RAMO 4: INTERPOLAZIONE TABELLE
             modalita_radiografia = "N/A"
             
             st.markdown("---")
             st.subheader("Parametri NCRP 147 (Tabelle 4.x)")
             
             # Modalità Radiografica (Stanza Radiografica / R&F)
             modalita_radiografia_ramo4 = st.selectbox(
                 "Modalità Tabella NCRP",
                 ["Stanza Radiografica", "R&F"]
             )
             
             tipo_barriera = st.selectbox("Tipo di Barriera", ["PRIMARIA", "SECONDARIA"])

             # Dettaglio Barriera
             dettagli_primari = ['chest buck wall', 'cross-table lateral wall', 'floor', 'wall opposite chest bucky']
             
             if tipo_barriera == "SECONDARIA":
                 dettaglio_hint = "Il calcolo Secondario (tabelle X.xc) usa i dati 'floor' come approssimazione generica."
                 default_index_dettaglio = dettagli_primari.index('floor')
                 preshielding = "NO" # Non rilevante per tabelle 'c'
             else:
                 dettaglio_hint = "Posizione specifica della barriera primaria (determina la colonna della tabella)."
                 default_index_dettaglio = 0
                 preshielding = st.selectbox("Pre-schermatura", ["NO", "SI"])

             dettaglio_barriera = st.selectbox(
                 "Dettaglio Barriera (Posizione)",
                 dettagli_primari,
                 index=default_index_dettaglio,
                 help=dettaglio_hint
             )

        
        materiale_schermatura = st.selectbox("Materiale Schermatura", ["PIOMBO", "CEMENTO"])
        
        # CAMPO kVp PER TC
        kvp_tc = "N/A" 
        if tipo_immagine == "TC":
            kvp_tc = st.selectbox(
                "Tensione di Picco (kVp) TC", 
                list(ATTENUATION_DATA_TC[materiale_schermatura].keys()),
                index=0
            )


    # COL 2: Input Numerici
    with col2:
        st.header("2. Dati di Esercizio")
        
        # Ora queste variabili sono definite nell'ambito di main_app()
        P_mSv_wk = st.number_input("Dose Limite (P) [mSv/settimana]", value=P_mSv_wk, format="%.3f") 
        tasso_occupazione_T = st.number_input("Tasso Occupazione (T) [0-1]", value=tasso_occupazione_T, format="%.2f", min_value=0.0, max_value=1.0)
        distanza_d = st.number_input("Distanza dalla Sorgente (d) [metri]", value=distanza_d, format="%.2f", min_value=0.1)
        
        fattore_uso_U = 1.0 # Default
        pazienti_settimana_N = 0 # Default

        
        if tipo_immagine == "RADIOLOGIA DIAGNOSTICA":
             fattore_uso_U = st.number_input("Fattore di Uso (U) [0-1]", value=0.25, format="%.2f", min_value=0.0, max_value=1.0)
             pazienti_settimana_N = st.number_input("Pazienti/Settimana (N)", value=100, min_value=1)
             
        elif tipo_immagine == "TC":
            st.markdown("---") 
            st.subheader("Ripartizione Esami Settimanali (N)")
            fattore_uso_U = 1.0
            pazienti_settimana_N = 0
            
            weekly_n_head = st.number_input("WEEKLY N HEAD PROCED", value=40, min_value=0)
            weekly_n_body = st.number_input("WEEKLY N BODY PROCED", value=60, min_value=0)

            contrast_factor = st.number_input("CONTRAST Factor ($K_c$)", value=1.4, min_value=1.0, max_value=2.0, format="%.1f")
            
        elif tipo_immagine == "RAMO 4: INTERPOLAZIONE TABELLE":
             st.markdown("---")
             st.subheader("Carico di Lavoro RAMO 4")
             # N in mAs/wk (input per la formula B^-1)
             N_input_ramo4 = st.number_input("$N$ (Carico di Lavoro mAs/wk)", min_value=1.0, value=500.0, step=100.0, format="%.2f")

        st.markdown("---") 
        
        # Logica X_PRE per RAMO 1/2/3
        X_PRE_value = 0.0
        X_PRE_selection_key = "Non Applicabile (RAMO 4)"
        if tipo_immagine != "RAMO 4: INTERPOLAZIONE TABELLE":
            if modalita_radiografia in ["RADIOGRAFIA TORACE", "STANZA RADIOGRAFICA (CHEST BUCKY)"]:
                options_x_pre = X_PRE_CROSS_TABLE_KEYS
                default_index = 1 if "PIOMBO (0.3 mm) - Cross-Table Lateral" in options_x_pre else 0
                help_text = "Schermatura intrinseca (Cross-Table Lateral)."
            else:
                options_x_pre = X_PRE_TABLE_HOLDER_KEYS
                default_index = 1 if "PIOMBO (0.85 mm) - Table/Holder" in options_x_pre else 0
                help_text = "Schermatura intrinseca (Table/Holder)."
                
            X_PRE_selection_key = st.selectbox(
                "Schermatura Pre-esistente ($X_{pre}$) [mm]", 
                options=options_x_pre,
                index=default_index, 
                help=help_text + " (Vedere Tabella 4.6 NCRP 147)."
            )
            X_PRE_value = PRESHIELDING_XPRE_OPTIONS[X_PRE_selection_key]


    # COL 3: Esecuzione
    with col3:
        st.header("3. Esecuzione")
        
        # Creazione del dizionario dei parametri
        params = {
            'tipo_immagine': tipo_immagine,
            'modalita_radiografia': modalita_radiografia,
            'tipo_barriera': tipo_barriera,
            'materiale_schermatura': materiale_schermatura,
            'P_mSv_wk': P_mSv_wk,
            'tasso_occupazione_T': tasso_occupazione_T,
            'distanza_d': distanza_d,
            'fattore_uso_U': fattore_uso_U,
            'pazienti_settimana_N': pazienti_settimana_N,
            'X_PRE_mm': X_PRE_value,
            
            # PARAMETRI SPECIFICI TC (RAMO 3)
            'weekly_n_head': weekly_n_head,
            'weekly_n_body': weekly_n_body,
            'contrast_factor': contrast_factor,
            'kvp_tc': kvp_tc,
            
            # PARAMETRI SPECIFICI RAMO 4
            'N_mAs_wk': N_input_ramo4,
            'modalita_radiografia_ramo4': modalita_radiografia_ramo4,
            'dettaglio_barriera': dettaglio_barriera,
            'preshielding': preshielding
        }
        
        if st.button("🟡 ESEGUI CALCOLO SCHERMATURA", type="primary"):
            st.session_state['results'] = None
            st.session_state['run'] = False
                
            results = run_shielding_calculation(params)
            st.session_state['results'] = results
            st.session_state['run'] = True


    st.markdown("---")
    
    # --- Sezione Output ---
    if 'run' in st.session_state and st.session_state['run']:
        results = st.session_state['results']
        st.header("Risultati del Calcolo")
        
        if 'errore' in results:
            st.error(f"❌ Errore Logico/Implementazione: {results['errore']}")
        else:
            st.success(f"✅ Calcolo Eseguito: **{results['ramo_logico']}**")
            
            # Unità di misura dinamica
            unita = params['materiale_schermatura']
            if results['ramo_logico'] == 'RAMO 4: INTERPOLAZIONE TABELLE (NCRP 147)':
                 unita = results.get('unita_misura', unita)
                 
            col_res1, col_res2, col_res3 = st.columns(3)
            col_res1.metric("Spessore Finale Richiesto (X)", f"**{results['spessore_finale_mm']:.2f} {unita}**")

            # Display Kerma/B dinamico
            if results['ramo_logico'] == 'RAMO 4: INTERPOLAZIONE TABELLE (NCRP 147)':
                 col_res2.metric("Numero TVL Richiesti ($n_{TVL}$)", f"{results.get('n_TVL_calc', 0.0):.2f}")
                 # B_inv = 10**n_TVL
                 B_inv = 10**results.get('n_TVL_calc', 0.0)
                 col_res3.metric("Fattore di Trasmittanza (B)", f"{1/B_inv:.4e}" if B_inv > 0 else "N/A")
            else:
                kerma_non_schermato = results.get('kerma_non_schermato', 0.0)
                col_res2.metric("Kerma Non Schermato ($K_{tu}$)", f"{kerma_non_schermato:.2e} mGy/settimana")
                B_calc = params['P_mSv_wk'] / (kerma_non_schermato * params['tasso_occupazione_T']) if kerma_non_schermato * params['tasso_occupazione_T'] > 0 else 0
                col_res3.metric("Fattore di Trasmittanza (B)", f"{B_calc:.4e}")

            # Display dettagli secondari
            st.subheader("Dettagli del Processo")
            
            if results['ramo_logico'] == 'RAMO 4: INTERPOLAZIONE TABELLE (NCRP 147)':
                st.markdown(f"### Dettagli Interpolazione")
                st.code(f"X = {results['spessore_finale_mm']:.2f} {results['unita_misura']}")
                # CORREZIONE QUI: USO LE VARIABILI DEFINITE NELL'AMBITO GLOBALE/INPUT
                st.write(f"I dati di input **N={N_input_ramo4:.2f} mAs/wk**, **T={tasso_occupazione_T:.2f}**, **P={P_mSv_wk*1000.0:.2f} µSv/wk**, e **d²={distanza_d**2:.2f} m²** hanno portato a:")
                st.code(f"n_TVL = log10(B⁻¹) = {results.get('n_TVL_calc', 0.0):.2f}")
                st.info(results['dettaglio'])
                
            elif results['ramo_logico'] == 'RAMO 3: TC (Calcolo Spessore)':
                  st.info(results['dettaglio'])
                  st.markdown("**Valori di Kerma $K_{1sec}$ calcolati (a 1 metro):**")
                  st.write(f"- $K_{{1sec}}(\\text{{Head}})$: {results.get('K1sec_head_mGy_paz', 0.0):.2e} mGy/paziente")
                  st.write(f"- $K_{{1sec}}(\\text{{Body}})$: {results.get('K1sec_body_mGy_paz', 0.0):.2e} mGy/paziente")
              
            else: # Ramo 1 e 2
                st.info(results['dettaglio'])
                if params['tipo_barriera'] == "SECONDARIA":
                    st.markdown("**Componenti Secondarie (Modello $K_{s1}$ Combinato):**")
                    st.write(f"- Spessore Fuga ($X_L$): {results.get('X_fuga_mm', 0.0):.2f} mm")
                    st.write(f"- Spessore Diffusione ($X_S$): {results.get('X_diffusione_mm', 0.0):.2f} mm")
                st.write(f"- $X_{{pre}}$ (Pre-schermatura): {params['X_PRE_mm']:.2f} mm (Selezionato: {X_PRE_selection_key})")
                
if __name__ == "__main__":
    if 'run' not in st.session_state:
        st.session_state['run'] = False
    if 'results' not in st.session_state:
        st.session_state['results'] = None
        
    main_app()