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

# NUOVA MAPPATURA PER LA SELEZIONE CATEGORICA DI X_PRE
X_PRE_CATEGORY_OPTIONS = {
    "GRID, CASSETTE, IMAGE-RECEPTOR": X_PRE_TABLE_HOLDER_KEYS, 
    "GRID, CASSETTE": X_PRE_CROSS_TABLE_KEYS
}


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
        'chest buck wall': np.array([90, 100, 110, 118, 122, 130, 133, 138, 140, 143, 145, 148, 150, 153, 155, 157, 160, 162, 164, 166, 167, 168, 170, 171, 172, 173, 174]),
        'cross-table lateral wall': np.array([45, 60, 70, 75, 80, 85, 90, 95, 98, 100, 102, 105, 107, 110, 112, 113, 114, 115, 117, 118, 119, 120, 121, 122, 123, 124, 125]),
        'wall opposite chest bucky': np.array([25, 40, 50, 55, 60, 65, 70, 72, 75, 78, 80, 83, 85, 87, 90, 92, 94, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105])
    }, 
    '4.8b': { # Primaria, Si preshielding
        'floor': np.array([50, 65, 75, 80, 85, 90, 95, 98, 100, 102, 105, 107, 110, 112, 114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127]),
        'cross-table lateral wall': np.array([40, 58, 68, 73, 78, 82, 86, 90, 93, 95, 97, 100, 102, 104, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118]),
        'chest buck wall': np.array([30, 40, 50, 60, 65, 70, 75, 78, 80, 83, 85, 88, 90, 92, 94, 95, 97, 98, 100, 101, 102, 103, 104, 105, 106, 107, 108]),
        'wall opposite chest bucky': np.array([20, 35, 45, 50, 55, 60, 65, 68, 70, 72, 75, 77, 80, 82, 84, 85, 86, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97])
    }, 
    '4.8c': { # Secondaria
        'floor': np.array([25, 40, 50, 55, 60, 65, 70, 72, 75, 78, 80, 83, 85, 87, 90, 92, 94, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105])
    }
}


# ====================================================================
# 2. FUNZIONI DI CALCOLO DELLA SCHERMATURA
# ====================================================================

def calcola_attenuazione_fitting(X_mm, alpha, beta, gamma):
    """
    Calcola il fattore di attenuazione B (inverso) in funzione dello spessore X 
    usando la formula di fitting NCRP 147: B^{-1} = alpha * (X + beta)^(-gamma)
    
    Args:
        X_mm (float): Spessore della barriera in mm di Piombo o Cemento.
        alpha (float): Parametro di fitting.
        beta (float): Parametro di fitting.
        gamma (float): Parametro di fitting.
        
    Returns:
        float: Fattore di attenuazione B (inverso), B_inverso.
    """
    if X_mm < 0:
        return 0.0 # B^-1 non può essere negativo
    try:
        B_inverso = alpha * (X_mm + beta)**(-gamma)
        return B_inverso
    except ValueError:
        return float('inf')


def calcola_attenuazione_tc_fitting(X_mm, alpha, beta, gamma):
    """
    Calcola il fattore di attenuazione B (inverso) per TC (Ramo 3)
    usando la formula NCRP 147 Eq A.2: B^{-1} = alpha * (X + beta)^(-gamma)
    
    Args:
        X_mm (float): Spessore della barriera in mm.
        alpha (float): Parametro di fitting.
        beta (float): Parametro di fitting.
        gamma (float): Parametro di fitting.
        
    Returns:
        float: Fattore di attenuazione B (inverso), B_inverso.
    """
    return calcola_attenuazione_fitting(X_mm, alpha, beta, gamma)


def calcola_schermatura(params):
    """
    Funzione principale per il calcolo della schermatura.
    
    Args:
        params (dict): Dizionario contenente tutti i parametri di input.
        
    Returns:
        dict: Dizionario con i risultati del calcolo e i dettagli.
    """
    
    tipo_barriera = params['tipo_barriera']
    materiale_barriera = params['materiale_barriera']
    design_goal_P = params['design_goal_P']
    occupancy_factor_T = params['occupancy_factor_T']
    distanza_d = params['distanza_d']
    X_PRE_mm = params['X_PRE_mm']
    
    
    # ----------------------------------------------------------------
    # LOGICA GENERALE NCRP 147
    # ----------------------------------------------------------------
    
    # T fattore: P design goal / T occupancy
    T_factor = design_goal_P / occupancy_factor_T
    
    # Inizializzazione dettagli per il log
    dettaglio = f"Obiettivo di Dose Settimanale ($P$) = {design_goal_P*1000:.2f} µSv/wk\n"
    dettaglio += f"Fattore di Occupazione ($T$) = {occupancy_factor_T:.2f}\n"
    dettaglio += f"Fattore di Progettazione ($P/T$) = {T_factor*1000:.2f} µSv/wk\n"
    dettaglio += f"Distanza Sorgente-Barriera ($d$) = {distanza_d:.2f} m\n"
    dettaglio += f"Materiale Barriera Selezionato: {materiale_barriera}"
    
    
    # ----------------------------------------------------------------
    # LOGICA PER RAMO 3: TC (Tomografia Computerizzata)
    # ----------------------------------------------------------------
    
    if tipo_barriera == 'TC (Calcolo Spessore)':
        ramo_logico = 'RAMO 3: TC (Calcolo Spessore)'
        dettaglio += f"\nModalità NCRP: {ramo_logico}"

        # Parametri TC
        tc_kvp = params['tc_kvp']
        weekly_n_head = params['weekly_n_head']
        weekly_n_body = params['weekly_n_body']
        
        # Kerma da Dose-Length Product (DLP) (Tabella 5.2)
        DLP_head = DLP_TC_FIXED_VALUES['HEAD'] # mGy*cm
        DLP_body = DLP_TC_FIXED_VALUES['BODY'] # mGy*cm
        
        # Coefficienti di Kerma (Tabella 5.2)
        K_diff_head = K_HEAD_DIFF # cm^-1
        K_diff_body = K_BODY_DIFF # cm^-1
        
        # Kerma per Paziente K1sec (alla distanza di 1 m) - Eq 5.3 NCRP 147
        K1sec_head_mGy_paz = (DLP_head * K_diff_head) / (100 * 4 * math.pi) 
        K1sec_body_mGy_paz = (DLP_body * K_diff_body) / (100 * 4 * math.pi)
        
        # Kerma Effettivo K_eff settimanale [mGy/wk]
        # In questo ramo, l'attenuazione (U) e il fattore di diffusione (a) sono inglobati 
        # nei valori di K1sec di riferimento.
        K_eff_head = K1sec_head_mGy_paz * weekly_n_head * (1/distanza_d**2)
        K_eff_body = K1sec_body_mGy_paz * weekly_n_body * (1/distanza_d**2)
        
        # Kerma totale K_eff
        K_eff = K_eff_head + K_eff_body
        
        dettaglio += f"\n- $K_{{1sec}}(\\text{{Head}})$ (a 1m): {K1sec_head_mGy_paz:.2e} mGy/paziente"
        dettaglio += f"\n- $K_{{1sec}}(\\text{{Body}})$ (a 1m): {K1sec_body_mGy_paz:.2e} mGy/paziente"
        dettaglio += f"\n- $W \\times K_{{1sec}}(\\text{{Head}})$: {K_eff_head:.2e} mGy/wk a $d^2$"
        dettaglio += f"\n- $W \\times K_{{1sec}}(\\text{{Body}})$: {K_eff_body:.2e} mGy/wk a $d^2$"
        dettaglio += f"\n$K_{{eff, tot}}$ (Calcolato) = {K_eff:.2e} mGy/wk a $d^2$"

        # Fattore di Attenuazione Inverso Richiesto B^(-1)
        B_inverso = T_factor / K_eff
        dettaglio += f"\n$B^{{-1}}$ (Totale Richiesto) = $P / (K_{{eff}} \\times T) = {B_inverso:.2e}"
        
        # Parametri di Fitting per TC (Tabella A.1 - Piombo/Cemento)
        attenuation_params = ATTENUATION_DATA_TC[materiale_barriera][tc_kvp]
        alpha = attenuation_params['alpha']
        beta = attenuation_params['beta']
        gamma = attenuation_params['gamma']
        
        # Calcolo di n_TVL e Spessore (X)
        n_TVL = np.log10(B_inverso)
        
        # Determina Spessore (X) risolvendo l'equazione del fitting
        # B^{-1} = alpha * (X + beta)^(-gamma)
        # B^{-1} / alpha = (X + beta)^(-gamma)
        # (B^{-1} / alpha)^(-1/gamma) = X + beta
        # X = (B^{-1} / alpha)^(-1/gamma) - beta
        
        spessore_X = (B_inverso / alpha)**(-1/gamma) - beta
        
        results = {
            'spessore_richiesto': spessore_X if spessore_X > 0 else 0.0,
            'materiale_barriera': materiale_barriera,
            'n_TVL_calc': n_TVL,
            'B_inverso': B_inverso,
            'ramo_logico': ramo_logico,
            'dettaglio': dettaglio,
            'K1sec_head_mGy_paz': K1sec_head_mGy_paz,
            'K1sec_body_mGy_paz': K1sec_body_mGy_paz,
        }
        return results

    # ----------------------------------------------------------------
    # LOGICA PER RAMO 1 & 2: Fitting Model (Primaria e Secondaria)
    # ----------------------------------------------------------------
    
    if tipo_barriera in ['PRIMARIA', 'SECONDARIA']:
        ramo_logico = params['ramo_logico'] # Ramo 1 o 2
        modalita_radiografia = params['modalita_radiografia']
        componente_secondaria = params['componente_secondaria']
        
        dettaglio += f"\nModalità NCRP: {modalita_radiografia} ({tipo_barriera})"

        # Estrazione dati K (Kerma) e Wnorm
        kerma_data = KERMA_DATA[modalita_radiografia]
        W_norm = kerma_data['Wnorm']
        U_tot = params['U_tot']
        
        # Kerma per la componente primaria (Kp1) o secondaria (Ksec1)
        if tipo_barriera == 'PRIMARIA':
            K_val = kerma_data['Kp1'] # mGy/paz. a 1m
            dettaglio += f"\n$K_{{val}}$ (NCRP 147) = $K_{{p1}} = {K_val:.2f}$ mGy/paz. a 1m"
            
        else: # SECONDARIA
            # Kerma secondario combinato Ksec1_Comb 
            K_val = kerma_data[componente_secondaria] # mGy*m^2/paz.
            dettaglio += f"\n$K_{{val}}$ (NCRP 147) = $K_{{s1}} ({componente_secondaria.split('_')[-1]}) = {K_val:.2e}$ mGy*m^2/paz."

        # Calcolo Kerma Effettivo K_eff
        # K_eff = K_val * U_tot * W / d^2 (in caso primario) 
        # K_eff = K_val * W / d^2 (in caso secondario, K_val è già Ksec1)
        
        # Poiché K_val è già corretto (K_p1 o K_s1) e W_norm è già incluso nel K_val:
        # K_eff = K_val * U_tot * (W / W_norm) / d^2 (solo per barriera primaria/secondaria che usa Wnorm)
        # La formula di base del Kerma Effettivo (NCRP 147 Eq 4.1) è: K_eff = K_val * (W / W_norm) * U_tot / d^2
        # Nel caso secondario K_val è K_s1 * W_norm (K_s1 è Ksec1)
        
        # Per mantenere la coerenza del fitting, si calcola K_eff = K_val * U_tot / d^2 (usando i Kp1/Ksec1 dalla Tabella)
        # e si applica il fattore W/Wnorm come correzione W_corr.
        
        # Per Ramo 1 e 2, la logica di K_eff per il fitting model è:
        # K_eff [mGy/settimana a 1m] = K_val * U_tot (uso il K_val dalla Tabella 4.5/4.7, che ha Wnorm implicito)
        K_eff = K_val * U_tot # Base formula
        
        # ----------------------------------------------------------------
        # CORREZIONE W_site (Ramo 1, 2)
        W_site = params['W_site']
        if W_site > 0.0:
            W_corr = W_site / W_norm
            K_eff = K_val * U_tot * W_corr # K_eff = K_val * U_tot * W_corr
            dettaglio += f"\nCorrezione $W_{{site}}$ applicata: $W_{{corr}} = W_{{site}} / W_{{norm}} = {W_site:.2f} / {W_norm:.2f} = {W_corr:.2f}"
            
        # Calcolo di B^(-1)
        # B^(-1) = P * d^2 / (K_eff * T)
        # N.B.: K_eff calcolato qui è K_val * U_tot * W_corr (a 1m). 
        # La formula completa: B_inverso = P_des * (distanza_d**2) / (K_eff * T_factor)
        # K_eff è già in mGy/paziente e la divisione per W_norm è implicita (o corretta con W_corr)
        # Dobbiamo dividere per d^2 per trovare il Kerma Atteso alla distanza d (K_eff / d^2)
        # E la formula del B_inverso è B_inverso = P / (K_eff_d * T) = P * d^2 / (K_eff_1m * T)
        B_inverso = design_goal_P * (distanza_d**2) / (K_eff * T_factor) 
        dettaglio += f"\n$B^{{-1}}$ (Totale Richiesto) = $P \\times d^2 / (K_{{eff}} \\times T) = {B_inverso:.2e}"
        
        # Fattore di attenuazione del Preshielding (B_pre)
        X_PRE_B_inverso = 1.0 # Nessun preshielding
        if X_PRE_mm > 0.0:
            attenuation_params_pre = ATTENUATION_DATA_PRIMARY[modalita_radiografia][materiale_barriera] # Usa sempre Primaria per X_PRE
            alpha = attenuation_params_pre['alpha']
            beta = attenuation_params_pre['beta']
            gamma = attenuation_params_pre['gamma']
            X_PRE_B_inverso = calcola_attenuazione_fitting(X_PRE_mm, alpha, beta, gamma)
            
        # B^(-1) Netto Richiesto
        B_netto_inverso = B_inverso / X_PRE_B_inverso
        
        # Selezione dei parametri di fitting (Primaria o Secondaria)
        if tipo_barriera == 'PRIMARIA':
            attenuation_data = ATTENUATION_DATA_PRIMARY
        else: # SECONDARIA
            attenuation_data = ATTENUATION_DATA_SECONDARY
            
        # Parametri di Fitting per la barriera principale
        attenuation_params = attenuation_data[modalita_radiografia][materiale_barriera]
        alpha = attenuation_params['alpha']
        beta = attenuation_params['beta']
        gamma = attenuation_params['gamma']
        
        # Calcolo di n_TVL e Spessore (X)
        n_TVL = np.log10(B_netto_inverso)
        spessore_X = (B_netto_inverso / alpha)**(-1/gamma) - beta
        
        # Calcolo del Kerma Fuga (solo per barriera secondaria - Ramo 2: Fluoro)
        X_fuga_mm = 0.0
        if tipo_barriera == 'SECONDARIA' and ramo_logico == 'RAMO 2: FLUOROSCOPIA (Fitting Model)':
             # X_fuga è lo spessore di Piombo richiesto per la componente di Fuga (Leak)
             # B_inverso_Leak = P * d^2 / (K_leak * T)
             K_val_leak = kerma_data['Ksec1_LeakSide'] # mGy*m^2/paz.
             K_eff_leak = K_val_leak * U_tot 
             
             # Correzione W_site anche per la componente Fuga
             if W_site > 0.0:
                 K_eff_leak *= W_corr
             
             B_inverso_leak = design_goal_P * (distanza_d**2) / (K_eff_leak * T_factor)
             n_TVL_leak = np.log10(B_inverso_leak)
             
             attenuation_params_pb = ATTENUATION_DATA_SECONDARY[modalita_radiografia]['PIOMBO'] # Fuga calcolata in Pb
             alpha_l = attenuation_params_pb['alpha']
             beta_l = attenuation_params_pb['beta']
             gamma_l = attenuation_params_pb['gamma']
             X_fuga_mm = (B_inverso_leak / alpha_l)**(-1/gamma_l) - beta_l
             
        
        results = {
            'spessore_richiesto': spessore_X if spessore_X > 0 else 0.0,
            'materiale_barriera': materiale_barriera,
            'n_TVL_calc': n_TVL,
            'B_inverso': B_inverso,
            'B_pre': X_PRE_B_inverso,
            'B_netto_inverso': B_netto_inverso,
            'ramo_logico': ramo_logico,
            'dettaglio': dettaglio,
            'X_fuga_mm': X_fuga_mm if X_fuga_mm > 0 else 0.0
        }
        return results

    # ----------------------------------------------------------------
    # LOGICA PER RAMO 4: Interpolazione Tabelle (Solo Radiografia)
    # ----------------------------------------------------------------
    
    if tipo_barriera == 'RAMO 4: INTERPOLAZIONE TABELLE':
        ramo_logico = 'RAMO 4: RADIOGRAFIA (Interpolazione Tabelle)'
        modalita_radiografia = params['modalita_radiografia'] # Qui in Ramo 4 è il tipo di parete (e.g. 'chest buck wall')
        is_preshielded = params['is_preshielded']
        
        # Estrazione dati K (Kerma) (Ramo 4 usa Kerma Kp1 o Ksec1 combinato)
        # I valori sono fissi: Kp1 per Primaria Chest/Floor (Tabella 4.5), Ksec1 per Secondaria (Tabella 4.7 Comb)
        if modalita_radiografia in ['chest buck wall', 'floor', 'cross-table lateral wall', 'wall opposite chest bucky']:
            # Logica per barriera PRIMARIA (uso Kp1 per il calcolo base, come da istruzioni fornite)
            
            # K_val per Ramo 4 (Primario) è il Kp1 della stanza Radiografica (Chest Bucky/Piano)
            if modalita_radiografia == 'chest buck wall':
                kerma_data = KERMA_DATA["STANZA RADIOGRAFICA (CHEST BUCKY)"]
            else:
                kerma_data = KERMA_DATA["STANZA RADIOGRAFICA (PIANO/ALTRE BARRIERE)"]
                
            K_val = kerma_data['Kp1'] # mGy/paz. a 1m
            U_tot = params['U_tot']
            
            dettaglio += f"\nModalità NCRP: STANZA RADIOGRAFICA (Primaria/Ramo 4)"
            dettaglio += f"\nParete Selezionata: {modalita_radiografia}"
            dettaglio += f"\n$K_{{val}}$ (NCRP 4.5) = $K_{{p1}} = {K_val:.2f}$ mGy/paz. a 1m"

            # Calcolo di B^(-1)
            # B_inverso = P * d^2 / (K_val * U * T)
            B_inverso = design_goal_P * (distanza_d**2) / (K_val * U_tot * T_factor)
            dettaglio += f"\n$B^{{-1}}_{{base}} = P \\times d^2 / (K_{{val}} \\times U \\times T) = {B_inverso:.2e}"
            
            # ----------------------------------------------------------------
            # CORREZIONE W_site (Ramo 4)
            W_site = params['W_site']
            if W_site > 0.0:
                # Definizione W_norm specifica per Ramo 4 (come da istruzioni)
                if modalita_radiografia == 'chest buck wall':
                    W_norm = 0.6
                else:
                    W_norm = 1.9 # Per 'floor', 'cross-table lateral wall', 'wall opposite chest bucky'

                W_corr = W_site / W_norm
                B_inverso *= W_corr # B_inverso_corretto = B_inverso_base * W_corr
                
                dettaglio += f"\nCorrezione $W_{{site}}$ applicata: $W_{{norm}}$ (Ramo 4) = {W_norm:.2f}. $W_{{corr}} = W_{{site}} / W_{{norm}} = {W_site:.2f} / {W_norm:.2f} = {W_corr:.2f}"
                
            # ----------------------------------------------------------------
                
            # Calcolo di n_TVL e Spessore (X)
            n_TVL = np.log10(B_inverso)
            
            # Selezione tabella corretta
            if materiale_barriera == 'PIOMBO':
                if is_preshielded:
                    ncrp_table_key = '4.5b'
                else:
                    ncrp_table_key = '4.5a'
            else: # CEMENTO
                if is_preshielded:
                    ncrp_table_key = '4.6b'
                else:
                    ncrp_table_key = '4.6a'
                    
            table_data = NCRP_TABLES[ncrp_table_key][modalita_radiografia]
            
            # Interpolazione
            n_indices = np.arange(0, 27) # Indici 0 a 26 (27 punti)
            interpolator = interp1d(n_indices, table_data, kind='linear')
            spessore_X = interpolator(n_TVL)
            
            
        else:
            # Logica per barriera SECONDARIA (usa Ksec1 combinato) - Si usa 'floor' per 4.5c/4.6c come base
            # Non ho una mappatura specifica delle pareti secondarie nelle tabelle 4.5c/4.6c, uso 'floor' come placeholder
            kerma_data = KERMA_DATA["STANZA RADIOGRAFICA (TUTTE BARRIERE)"]
            K_val = kerma_data['Ksec1_Comb'] # mGy*m^2/paz.
            U_tot = params['U_tot']
            
            dettaglio += f"\nModalità NCRP: STANZA RADIOGRAFICA (Secondaria/Ramo 4)"
            dettaglio += f"\n$K_{{val}}$ (NCRP 4.7 Comb) = $K_{{s1, Comb}} = {K_val:.2e}$ mGy*m^2/paz."
            
            # Calcolo di B^(-1)
            B_inverso = design_goal_P * (distanza_d**2) / (K_val * U_tot * T_factor)
            dettaglio += f"\n$B^{{-1}}_{{base}} = P \\times d^2 / (K_{{val}} \\times U \\times T) = {B_inverso:.2e}"
            
            # ----------------------------------------------------------------
            # CORREZIONE W_site (Ramo 4 - Secondaria)
            W_site = params['W_site']
            if W_site > 0.0:
                # W_norm per Secondaria: 2.5 (da KERMA_DATA["STANZA RADIOGRAFICA (TUTTE BARRIERE)"])
                W_norm = 2.5
                W_corr = W_site / W_norm
                B_inverso *= W_corr 
                
                dettaglio += f"\nCorrezione $W_{{site}}$ applicata: $W_{{norm}}$ (Secondaria) = {W_norm:.2f}. $W_{{corr}} = W_{{site}} / W_{{norm}} = {W_site:.2f} / {W_norm:.2f} = {W_corr:.2f}"
            
            # ----------------------------------------------------------------

            # Calcolo di n_TVL e Spessore (X)
            n_TVL = np.log10(B_inverso)
            
            # Selezione tabella corretta
            if materiale_barriera == 'PIOMBO':
                ncrp_table_key = '4.5c'
            else: # CEMENTO
                ncrp_table_key = '4.6c'
                
            # Uso la chiave 'floor' come rappresentante della barriera secondaria nelle tabelle 4.5c/4.6c
            table_data = NCRP_TABLES[ncrp_table_key]['floor']
            
            # Interpolazione
            n_indices = np.arange(0, 27) 
            interpolator = interp1d(n_indices, table_data, kind='linear')
            spessore_X = interpolator(n_TVL)
            
        
        results = {
            'spessore_richiesto': spessore_X if spessore_X > 0 else 0.0,
            'materiale_barriera': materiale_barriera,
            'n_TVL_calc': n_TVL,
            'B_inverso': B_inverso,
            'ramo_logico': ramo_logico,
            'dettaglio': dettaglio
        }
        return results

    # ----------------------------------------------------------------
    # Nessun Ramo Logico Selezionato o Caso non contemplato
    # ----------------------------------------------------------------

    return {
        'spessore_richiesto': 0.0,
        'materiale_barriera': materiale_barriera,
        'n_TVL_calc': 0.0,
        'B_inverso': 0.0,
        'ramo_logico': 'ERRORE: Ramo Logico non identificato',
        'dettaglio': 'Selezionare una Modalità di Calcolo (Tipo Barriera/Ramo Logico) valida.',
    }


# ====================================================================
# 3. INTERFACCIA UTENTE STREAMLIT
# ====================================================================

def main_app():
    st.title("Calcolo Schermature Radiologiche (NCRP 147) 🛡️")
    st.markdown("---")
    
    # ----------------------------------------------------------------
    # SIDEBAR: Selezioni Principali
    # ----------------------------------------------------------------
    st.sidebar.title("Parametri Principali")
    
    # Selezione Tipo di Barriera e Ramo Logico (determina la modalità di calcolo)
    tipo_barriera_options = [
        "PRIMARIA", 
        "SECONDARIA",
        "TC (Calcolo Spessore)",
        "RAMO 4: INTERPOLAZIONE TABELLE" # Nuova modalità per Ramo 4
    ]
    tipo_barriera = st.sidebar.selectbox("Tipo di Barriera", tipo_barriera_options)
    
    # Selezione del Design Goal P (Dose Massima Ammissibile Settimanale)
    design_goal_options = {
        "100 µSv/wk (Non-occupazionale)": 100e-6, # 0.1 mSv/wk -> 100 uSv/wk -> 100e-6 Sv/wk
        "1000 µSv/wk (Occupazionale)": 1000e-6, # 1.0 mSv/wk -> 1000 uSv/wk -> 1000e-6 Sv/wk
        "20 µSv/wk (UK/Europa - Valore cautelativo)": 20e-6 # 20 uSv/wk -> 20e-6 Sv/wk
    }
    design_goal_label = st.sidebar.selectbox("Obiettivo di Dose Settimanale ($P$)", list(design_goal_options.keys()))
    design_goal_P = design_goal_options[design_goal_label]
    
    # Fattore di Occupazione T
    occupancy_factor_T = st.sidebar.slider("Fattore di Occupazione ($T$) [0.0 - 1.0]", min_value=0.0, max_value=1.0, value=0.5, step=0.01)
    
    # Distanza Sorgente-Barriera d
    distanza_d = st.sidebar.number_input("Distanza Sorgente-Barriera ($d$) [metri]", min_value=0.1, value=2.0, step=0.1)

    # Materiale della Barriera
    materiale_barriera = st.sidebar.selectbox("Materiale della Barriera", ["PIOMBO", "CEMENTO"])
    
    # ----------------------------------------------------------------
    # LOGICA DI INIZIALIZZAZIONE
    # ----------------------------------------------------------------
    
    # Determinazione del Ramo Logico (per la visualizzazione e la logica di K_eff)
    if tipo_barriera == "TC (Calcolo Spessore)":
        ramo_logico = 'RAMO 3: TC (Calcolo Spessore)'
    elif tipo_barriera == "RAMO 4: INTERPOLAZIONE TABELLE":
        ramo_logico = 'RAMO 4: RADIOGRAFIA (Interpolazione Tabelle)'
    else: # PRIMARIA / SECONDARIA (Ramo 1 o 2)
        # Il Ramo 1/2 è determinato dalla Modalità Radiografica selezionata
        ramo_logico = None # Verrà aggiornato dopo la selezione
        
        
    # Inizializzazione variabili per ramo 1, 2, 4 (Radiografia)
    utilizzo_U = 0.0
    weekly_n_max = 0.0
    U_tot = 0.0
    componente_secondaria = 'Ksec1_Comb'
    # Inizializzazione W_site
    W_site = 0.0

    # Inizializzazione variabili per ramo 3 (TC)
    tc_kvp = "120 kVp"
    weekly_n_head = 0.0
    weekly_n_body = 0.0
    
    # Preshielding (X_PRE)
    X_PRE_mm = 0.0
    X_PRE_selection_key = "NESSUNO (0.0 mm) - Table/Holder"
    is_preshielded = False

    
    # ----------------------------------------------------------------
    # SEZIONI DI INPUT DINAMICHE
    # ----------------------------------------------------------------

    with st.container():
        
        # ----------------------------------------------------------------
        # RAMO 3: TC (Tomografia Computerizzata)
        # ----------------------------------------------------------------
        if ramo_logico == 'RAMO 3: TC (Calcolo Spessore)':
            st.markdown("### 2. Parametri di Input per TC (Ramo 3)")
            tc_kvp = st.selectbox("kVp (Tensione del Tubo)", ["120 kVp", "140 kVp"])
            weekly_n_head = st.number_input('Numero di Esami Testa/Settimana ($N_{Head}$)', min_value=0.0, value=50.0, step=1.0)
            weekly_n_body = st.number_input('Numero di Esami Corpo/Settimana ($N_{Body}$)', min_value=0.0, value=100.0, step=1.0)
            
            # In TC non si usa U e X_PRE è sempre 0 per il calcolo base
            
        # ----------------------------------------------------------------
        # RAMO 1, 2, 4: Radiografia/Fluoroscopia
        # ----------------------------------------------------------------
        else:
            
            st.markdown("### 2. Configurazione Radiografica e Barriera")

            if tipo_barriera in ['PRIMARIA', 'SECONDARIA']:
                # Selezione Modalità Radiografica (che determina Ramo 1 o 2)
                modalita_radiografia_options = list(ATTENUATION_DATA_PRIMARY.keys()) 
                modalita_radiografia = st.selectbox("Modalità NCRP (per $K_{p1}/K_{s1}$)", modalita_radiografia_options)
                
                # Determinazione Ramo Logico (1: Radiografia, 2: Fluoroscopia)
                if 'FLUOROSCOPIA' in modalita_radiografia or 'ANGIO' in modalita_radiografia:
                    ramo_logico = 'RAMO 2: FLUOROSCOPIA (Fitting Model)'
                else:
                    ramo_logico = 'RAMO 1: RADIOGRAFIA (Fitting Model)'
                st.info(f"Ramo Logico: **{ramo_logico}**")


            elif tipo_barriera == 'RAMO 4: INTERPOLAZIONE TABELLE':
                # Selezione Parete (modalita_radiografia diventa il tipo di parete)
                modalita_radiografia_options_4 = list(NCRP_TABLES['4.5a'].keys())
                # Aggiungo un placeholder per la secondaria
                modalita_radiografia_options_4.append('SECONDARIA (usa Tab. 4.5c/4.6c - Floor)')
                modalita_radiografia = st.selectbox("Tipo di Parete / Barriera", modalita_radiografia_options_4)
                
                # Ramo 4 usa solo le modalità di radiografia standard (STANZA RADIOGRAFICA) 
                # e non la classificazione del Ramo 1/2.
                
            
            st.markdown("---")
            st.markdown("### 3. Fattori Operativi (W, U, T) e Preshielding")
            
            # Input specifici per Ramo 1, 2, 4 (Radiografia/Fluoro/R&F con Fitting o Tabelle)
            if ramo_logico in ['RAMO 1: RADIOGRAFIA (Fitting Model)', 'RAMO 2: FLUOROSCOPIA (Fitting Model)', 'RAMO 4: RADIOGRAFIA (Interpolazione Tabelle)']:
                
                # Input U, W
                utilizzo_U = st.number_input('Fattore di Utilizzo ($U$) [0.0 - 1.0]', min_value=0.0, max_value=1.0, value=1.0)
                weekly_n_max = st.number_input('Carico di Lavoro Settimanale ($W_{max}$) [mA*min/settimana]', min_value=0.0, value=2500.0)
                U_tot = weekly_n_max / 1000.0 # W/1000 [mA*min/settimana / (mA*min/wk/1000)]
                st.caption(f"$U_{{tot}} = W_{{max}} / 1000 = {U_tot:.1f}$ (Valore utilizzato nel calcolo)")
                
                # Aggiunta Input W_site (Carico di Lavoro per il Sito)
                W_site = st.number_input('Input $W_{site}$ (Carico di Lavoro per il Sito) [mA*min/settimana]', min_value=0.0, value=0.0)
                st.caption("Se $W_{site} > 0.0$, viene applicato un fattore di correzione $W_{corr} = W_{site} / W_{norm}$")

                if tipo_barriera == "SECONDARIA":
                    # Selezione componente secondaria (Leakside, Forback, Combined)
                    componente_secondaria = st.selectbox(
                        "Componente Secondaria ($K_{s1}$)",
                        ['Ksec1_Comb', 'Ksec1_LeakSide', 'Ksec1_ForBack']
                    )
                
                # Input X_PRE (Preshielding)
                if ramo_logico == 'RAMO 4: RADIOGRAFIA (Interpolazione Tabelle)':
                    # In Ramo 4, l'input X_PRE è solo un toggle (Si/No)
                    is_preshielded = st.checkbox('Preshielding ($X_{pre}$) presente?', value=False)
                    if is_preshielded:
                        st.info("La presenza di Preshielding verrà gestita selezionando le tabelle NCRP 4.5b/4.6b o 4.7b/4.8b.")
                    X_PRE_mm = 0.0 # Non usato nel calcolo Ramo 4, ma nel selettore della tabella
                else: # Ramo 1 e 2: input di spessore
                    st.markdown("---")
                    st.markdown("#### Preshielding ($X_{pre}$)")
                    X_PRE_category = st.selectbox(
                        "Categoria Preshielding",
                        list(X_PRE_CATEGORY_OPTIONS.keys())
                    )
                    X_PRE_selection_key = st.selectbox(
                        "Spessore Preshielding ($X_{pre}$)",
                        X_PRE_CATEGORY_OPTIONS[X_PRE_category]
                    )
                    X_PRE_mm = PRESHIELDING_XPRE_OPTIONS[X_PRE_selection_key]
                
                

    # ----------------------------------------------------------------
    # ESECUZIONE DEL CALCOLO
    # ----------------------------------------------------------------
    
    # Dizionario dei parametri di input
    params = {
        'tipo_barriera': tipo_barriera,
        'modalita_radiografia': modalita_radiografia if tipo_barriera != "TC (Calcolo Spessore)" else "N/A",
        'materiale_barriera': materiale_barriera,
        'occupancy_factor_T': occupancy_factor_T,
        'design_goal_P': design_goal_P,
        'design_goal_P_label': design_goal_label.split(' ')[0],
        'distanza_d': distanza_d,
        'X_PRE_mm': X_PRE_mm if tipo_barriera not in ["TC (Calcolo Spessore)", "RAMO 4: INTERPOLAZIONE TABELLE"] else 0.0, # X_PRE solo per Ramo 1/2
        
        # Parametri Ramo 1, 2, 4
        'U_tot': U_tot,
        'utilizzo_U': utilizzo_U,
        'weekly_n_max': weekly_n_max,
        'componente_secondaria': componente_secondaria, # NUOVO PARAMETRO Ksec1
        'W_site': W_site, # NUOVO INPUT Wsite
        
        # Parametri Ramo 3 (TC)
        'tc_kvp': tc_kvp if tipo_barriera == "TC (Calcolo Spessore)" else "120 kVp",
        'weekly_n_head': weekly_n_head,
        'weekly_n_body': weekly_n_body,
        
        # Parametri Ramo 4
        'is_preshielded': is_preshielded if tipo_barriera == "RAMO 4: INTERPOLAZIONE TABELLE" else False,
        'ramo_logico': ramo_logico # Passa il ramo logico aggiornato per Ramo 1 e 2
    }


    if st.button('Calcola Spessore di Schermatura'):
        
        if (ramo_logico == 'RAMO 3: TC (Calcolo Spessore)') and (weekly_n_head <= 0 and weekly_n_body <= 0):
            st.error("Inserire un Carico di Lavoro Settimanale ($N_{Head}$ o $N_{Body}$) maggiore di zero per il calcolo TC.")
        elif ramo_logico in ['RAMO 1: RADIOGRAFIA (Fitting Model)', 'RAMO 2: FLUOROSCOPIA (Fitting Model)'] and weekly_n_max <= 0:
            st.error("Inserire un Carico di Lavoro Settimanale ($W_{max}$) maggiore di zero.")
        elif ramo_logico == 'RAMO 4: RADIOGRAFIA (Interpolazione Tabelle)' and weekly_n_max <= 0:
            st.error("Inserire un Carico di Lavoro Settimanale ($W_{max}$) maggiore di zero.")
        else:
            results = calcola_schermatura(params)
            
            st.markdown("---")
            st.header("Risultati del Calcolo")
            
            # Formattazione Output
            distanza_d = params['distanza_d']
            
            # Output per Ramo 4 (Interpolazione)
            if results['ramo_logico'] == 'RAMO 4: RADIOGRAFIA (Interpolazione Tabelle)':
                
                # Check per valore fuori range
                if results['n_TVL_calc'] < 0 or results['n_TVL_calc'] > 26:
                    st.error(f"ATTENZIONE: Il valore di $n_{{TVL}} = {results['n_TVL_calc']:.2f}$ è fuori dal range di interpolazione (0-26).")
                    st.warning("Lo spessore calcolato potrebbe essere non affidabile. Rivedere i parametri di input.")
                
                st.markdown(f"**Spessore Richiesto: ** **{results['spessore_richiesto']:.2f} mm {results['materiale_barriera']}**")
                
                st.markdown(f"**Dettagli di Calcolo ($P={params['design_goal_P']*1000:.2f} µSv/wk$, $T={params['occupancy_factor_T']:.2f}$, $d^2={distanza_d**2:.2f}$ m²):**")
                st.code(f"n_TVL = log10(B⁻¹) = {results.get('n_TVL_calc', 0.0):.2f}")
                st.info(results['dettaglio'])
                
                st.markdown(f"**Parametri di Input:**")
                st.write(f"- $U_{{tot}}$ (Carico): {params['U_tot']:.1f}")
                st.write(f"- $W_{{max}}$ (Input): {params['weekly_n_max']:.1f} mA*min/settimana")
                st.write(f"- $W_{{site}}$ (Input): {params['W_site']:.1f} mA*min/settimana")
                st.write(f"- $X_{{pre}}$ (Pre-schermatura): {'Sì (Tabella selezionata)' if params['is_preshielded'] else 'No'}")
                
            # Output per Ramo 3 (TC)
            elif results['ramo_logico'] == 'RAMO 3: TC (Calcolo Spessore)':
                  
                  if results['spessore_richiesto'] < 0:
                      st.success(f"**Spessore Richiesto: ** **0.00 mm {results['materiale_barriera']}**")
                      st.info("Il Kerma effettivo calcolato è inferiore al Design Goal. Non è richiesta schermatura aggiuntiva.")
                  else:
                      st.markdown(f"**Spessore Richiesto: ** **{results['spessore_richiesto']:.2f} mm {results['materiale_barriera']}**")
                      
                  st.markdown(f"**Dettagli di Calcolo ($P={params['design_goal_P']*1000:.2f} µSv/wk$, $T={params['occupancy_factor_T']:.2f}$, $d^2={distanza_d**2:.2f}$ m²):**")
                  st.code(f"n_TVL = log10(B⁻¹) = {results.get('n_TVL_calc', 0.0):.2f}")
                  st.info(results['dettaglio'])
                  
                  st.markdown("**Valori di Kerma $K_{1sec}$ calcolati (a 1 metro):**")
                  st.write(f"- $K_{{1sec}}(\\text{{Head}})$: {results.get('K1sec_head_mGy_paz', 0.0):.2e} mGy/paziente")
                  st.write(f"- $K_{{1sec}}(\\text{{Body}})$: {results.get('K1sec_body_mGy_paz', 0.0):.2e} mGy/paziente")
                  
                  st.markdown(f"**Parametri di Input:**")
                  st.write(f"- $N_{{\\text{{Head}}}}$/Settimana: {params['weekly_n_head']}")
                  st.write(f"- $N_{{\\text{{Body}}}}$/Settimana: {params['weekly_n_body']}")
              
            else: # Ramo 1 e 2 (Fitting)
                
                if results['spessore_richiesto'] < 0:
                     st.success(f"**Spessore Richiesto: ** **0.00 mm {results['materiale_barriera']}**")
                     st.info("Il Kerma effettivo calcolato è inferiore al Design Goal. Non è richiesta schermatura aggiuntiva.")
                else:
                    st.markdown(f"**Spessore Richiesto: ** **{results['spessore_richiesto']:.2f} mm {results['materiale_barriera']}**")
                
                st.markdown(f"**Fattori di Attenuazione:**")
                st.write(f"- $B_{{tot}}^{{-1}}$ (Totale Richiesto): **{results['B_inverso']:.2e}**")
                st.write(f"- $B_{{pre}}$ (Pre-schermatura): **{results['B_pre']:.2e}**")
                st.write(f"- $B_{{netto}}^{{-1}}$ (Netto Richiesto): **{results['B_netto_inverso']:.2e}**")
                
                st.markdown(f"**Dettagli di Calcolo ($P={params['design_goal_P']*1000:.2f} µSv/wk$, $T={params['occupancy_factor_T']:.2f}$, $d^2={distanza_d**2:.2f}$ m²):**")
                st.code(f"n_TVL = log10(B⁻¹_netto) = {results.get('n_TVL_calc', 0.0):.2f}")
                st.info(results['dettaglio'])
                
                st.markdown(f"**Parametri di Input:**")
                
                # Mostra Kp1 o Ksec1 combinato
                if params['tipo_barriera'] == "PRIMARIA":
                    st.write(f"- $K_{{p1}}$ (NCRP 4.5): {KERMA_DATA[params['modalita_radiografia']]['Kp1']:.2f} mGy/paz. a 1m")
                    st.write(f"- $U_{{tot}}$ (Carico): {params['U_tot']:.1f}")
                else: # SECONDARIA
                    st.write(f"- $K_{{s1}} ({params['componente_secondaria'].split('_')[-1]})$ (NCRP 4.7): {KERMA_DATA[params['modalita_radiografia']][params['componente_secondaria']]:.2e} mGy*m²/paz.")
                    st.write(f"- $U_{{tot}}$ (Carico): {params['U_tot']:.1f}")
                
                st.write(f"- $W_{{site}}$ (Input): {params['W_site']:.1f} mA*min/settimana")
                
                if params['tipo_barriera'] == "SECONDARIA":
                    st.markdown("**Componenti Secondarie Aggiuntive:**")
                    st.write(f"- Spessore Fuga ($X_L$): {results.get('X_fuga_mm', 0.0):.2f} mm Piombo (Solo per Ramo 2/Fluoro)")


if __name__ == "__main__":
    main_app()