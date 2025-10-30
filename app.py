import streamlit as st
import math


# ====================================================================
# 1. DATI NCRP 147 CONSOLIDATI
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
        'Kp1': None, # Usato per barriere secondarie
        'Ksec1_LeakSide': 3.2e-1, # 3.2*10^-1
        'Ksec1_ForBack': 4.4e-1, # 4.4*10^-1
        'Ksec1_Comb': 4.6e-1,
    },
    # 5. TUBO RADIOGENO STANZA R&F
    "RADIOGRAFIA (TUBO R&F)": {
        'Wnorm': 1.5,
        'Kp1': 5.9, # Kp1 da Tab 4.5 (Se la barriera è primaria)
        'Ksec1_LeakSide': 2.9e-2, # 2.9*10^-2
        'Ksec1_ForBack': 3.9e-2, # 3.9*10^-2
        'Ksec1_Comb': 4.0e-2, # Corretto 4.0*0-2 a 4.0*10^-2
    },
    # 6. STANZA RADIOGRAFICA TORACE (CHEST ROOM) - NOME AGGIORNATO
    "STANZA RADIOGRAFICA TORACE(CHEST ROOM)": {
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
    "STANZA RADIOGRAFICA TORACE(CHEST ROOM)": {
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
    "STANZA RADIOGRAFICA TORACE(CHEST ROOM)": {
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


# Parametri di Fitting (Alfa, Beta, Gamma) per Barriera TC (RAMO 3)
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


# ====================================================================
# NUOVE MAPPATURE LOGICHE DEFINITE DALL'UTENTE
# ====================================================================

# Tutte le chiavi di KERMA_DATA da mostrare nella UI (include TUTTE BARRIERE)
MODALITA_RADIOGRAFIA_UI_OPTIONS = list(KERMA_DATA.keys()) 

# Chiavi che seguono la logica del RAMO 1 (Diagnostica Standard)
RAMO_1_MODES = [
    "STANZA RADIOGRAFICA (CHEST BUCKY)",
    "STANZA RADIOGRAFICA (PIANO/ALTRE BARRIERE)",
    "RADIOGRAFIA (TUBO R&F)",
    "STANZA RADIOGRAFICA TORACE(CHEST ROOM)", 
]

# Chiavi che seguono la logica del RAMO 2 (Diagnostica Specializzata/Fluoro/Generica)
RAMO_2_MODES = [
    k for k in MODALITA_RADIOGRAFIA_UI_OPTIONS if k not in RAMO_1_MODES
]


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
        # $K_{incidente}$ (mGy/settimana)
        # $K_{tu} = (K_{val} \cdot U \cdot N) / d^2$
        kerma = (K_val * U * N) / (d ** 2)
        return kerma
    except Exception:
        return 0.0


# ====================================================================
# 3. FUNZIONI DI CALCOLO SPECIFICHE (RAMO 1 & 2)
# ====================================================================


def calculate_primary_thickness(params):
    """ 
    Implementa il calcolo Primario (Ramo 1). 
    Usa la chiave esatta selezionata dalla UI.
    """
    P = params.get('P_mSv_wk', 0.0) 
    T = params.get('tasso_occupazione_T', 1.0)
    d = params.get('distanza_d', 2.0)
    U = params.get('fattore_uso_U', 0.25)
    N = params.get('pazienti_settimana_N', 100)
    modalita = params.get('modalita_radiografia')
    materiale = params.get('materiale_schermatura')
    Xpre = params.get('X_PRE_mm', 0.0) 

    # Usa la chiave selezionata dall'utente direttamente.
    modalita_key = modalita
    
    # Kp1 è in mGy*m^2 / mAs
    Kp1_data = KERMA_DATA.get(modalita_key, {}).get('Kp1')
    
    # Se Kp1 è None, gestisce l'errore.
    if Kp1_data is None:
        return 0.0, 0.0, f"Dati Kp1 non definiti per la modalità '{modalita}' o non è prevista una barriera Primaria NCRP 147."

    
    if modalita_key not in ATTENUATION_DATA_PRIMARY or materiale not in ATTENUATION_DATA_PRIMARY[modalita_key]:
        return 0.0, 0.0, f"Dati di attenuazione Primaria mancanti per '{modalita_key}'."
        
    data = ATTENUATION_DATA_PRIMARY[modalita_key][materiale]
    alpha, beta, gamma = data['alpha'], data['beta'], data['gamma']
    
    # 1. Kerma non schermato (incidente)
    kerma_non_schermato_mGy_wk = calcola_kerma_incidente(Kp1_data, U, N, d)
    
    if kerma_non_schermato_mGy_wk * T == 0 or P == 0:
        return 0.0, 0.0, "Kerma o Tasso di Occupazione (T) o Dose Limite (P) nullo/i."
        
    # 2. Fattore di Trasmittanza B
    B_P = P / (kerma_non_schermato_mGy_wk * T)
    
    # 3. Spessore di Riferimento Xref
    Xref_mm = calcola_spessore_x(alpha, beta, gamma, B_P)
    
    # 4. Spessore Finale (Xref - Xpre)
    Xfinale_mm = max(0.0, Xref_mm - Xpre)
    
    log_msg = f"Kp1={Kp1_data:.2f}. B={B_P:.4e}. Xref={Xref_mm:.2f}mm. Xpre={Xpre:.2f}mm. Modalità NCRP: {modalita_key}"
    return Xfinale_mm, kerma_non_schermato_mGy_wk, log_msg


def calculate_secondary_thickness(params):
    """ 
    Implementa il calcolo Secondario (Ramo 1/2). 
    Usa la chiave esatta selezionata dalla UI.
    """
    P = params.get('P_mSv_wk', 0.0) 
    T = params.get('tasso_occupazione_T', 1.0)
    d = params.get('distanza_d', 2.0)
    U = 1.0 # U è tipicamente 1.0 per la secondaria (NCRP 147 Eq. 4.4)
    N = params.get('pazienti_settimana_N', 100)
    modalita = params.get('modalita_radiografia')
    materiale = params.get('materiale_schermatura')
    Xpre = params.get('X_PRE_mm', 0.0) 

    # Usa la chiave selezionata dall'utente direttamente.
    modalita_key = modalita
    
    # Ksec1 è in mGy*m^2 / mAs o mGy*m^2 / min
    Ksec1_data = KERMA_DATA.get(modalita_key, {}).get('Ksec1_Comb')
    if Ksec1_data is None:
        return 0.0, 0.0, 0.0, 0.0, f"Dati Ksec1_Comb non definiti per la modalità '{modalita_key}'."

    
    if modalita_key not in ATTENUATION_DATA_SECONDARY or materiale not in ATTENUATION_DATA_SECONDARY[modalita_key]:
        return 0.0, 0.0, 0.0, 0.0, f"Dati di attenuazione Secondaria mancanti per '{modalita_key}'."
        
    data = ATTENUATION_DATA_SECONDARY[modalita_key][materiale]
    alpha, beta, gamma = data['alpha'], data['beta'], data['gamma']
    
    # 1. Kerma non schermato (incidente)
    # $K_{tu} = (K_{s1} \cdot U \cdot N) / d^2$. Utilizziamo U=1 per la secondaria come da NCRP 147 Eq. 4.4
    kerma_non_schermato_mGy_wk = calcola_kerma_incidente(Ksec1_data, U, N, d)
    
    if kerma_non_schermato_mGy_wk * T == 0 or P == 0:
        return 0.0, 0.0, 0.0, 0.0, "Kerma o Tasso di Occupazione (T) o Dose Limite (P) nullo/i."
        
    # 2. Fattore di Trasmittanza B
    B_S = P / (kerma_non_schermato_mGy_wk * T)
    
    # 3. Spessore di Riferimento Xref
    Xref_mm = calcola_spessore_x(alpha, beta, gamma, B_S)
    
    # 4. Spessore Finale (Xref - Xpre)
    Xfinale_mm = max(0.0, Xref_mm - Xpre)
    
    log_msg = f"Ksec1={Ksec1_data:.4e}. B={B_S:.4e}. Xref={Xref_mm:.2f}mm. Xpre={Xpre:.2f}mm. (Modello combinato Ksec1, Modalità NCRP: {modalita_key})"
    
    # Nel modello combinato Ksec1, X_L = X_S = X_finale
    return Xfinale_mm, Xfinale_mm, Xfinale_mm, kerma_non_schermato_mGy_wk, log_msg


def calculate_special_secondary_thickness(params):
    """ Implementa il calcolo Secondario (Ramo 2). Stesso flusso logico di Ramo 1. """
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
    
    # Parametri specifici TC (Recuperati da params)
    N_head = params.get('weekly_n_head', 0) 
    N_body = params.get('weekly_n_body', 0)
    Kc = params.get('contrast_factor', 1.0) # Fattore di Contrasto
    kvp = params.get('kvp_tc')
    
    # --- 1. Calcolo del Kerma non schermato a 1m per paziente (K1sec) ---
    # K1sec(head) = khead * DLP_head * Kc (Eq. 5.1 NCRP 147)
    dlp_head = DLP_TC_FIXED_VALUES["HEAD"]
    K1sec_head_mGy_paz = K_HEAD_DIFF * dlp_head * Kc # [cm^-1] * [mGy*cm] * [] = [mGy]
    
    # K1sec(body) = 1.2 * kbody * DLP_body * Kc (Eq. 5.2 NCRP 147)
    dlp_body = DLP_TC_FIXED_VALUES["BODY"]
    K1sec_body_mGy_paz = 1.2 * K_BODY_DIFF * dlp_body * Kc 
    
    # --- 2. Calcolo del Kerma non schermato totale settimanale alla distanza d ($K_{tu}$) ---
    # $K_{tu}$ (a 1m) = (K1sec(head) * N_head) + (K1sec(body) * N_body) (Eq. 5.3 NCRP 147)
    total_kerma_at_1m_mGy_wk = (K1sec_head_mGy_paz * N_head) + (K1sec_body_mGy_paz * N_body)
    
    if d <= 0:
        kerma_tc_non_schermato_mGy_wk = 0.0
    else:
        # $K_{tu}$ (Kerma Settimanale alla distanza d)
        # $K_{tu}(d) = K_{tu}(1m) / d^2$ (d in metri, Kerma in mGy/wk)
        kerma_tc_non_schermato_mGy_wk = (1 / (d ** 2)) * total_kerma_at_1m_mGy_wk
    
    # --- 3. Calcolo del Fattore di Trasmittanza B ($B_{T}$) ---
    if kerma_tc_non_schermato_mGy_wk * T <= 0 or P == 0:
        B_T = 1.0 
    else:
        # $B = P / (K_{tu} \cdot T)$ (Eq. 5.4 NCRP 147)
        B_T = P / (T * kerma_tc_non_schermato_mGy_wk)
        
    # --- 4. Calcolo dello Spessore X richiesto (Usa i nuovi dati ATTENUATION_DATA_TC) ---
    
    if materiale not in ATTENUATION_DATA_TC or kvp not in ATTENUATION_DATA_TC[materiale]:
        return 0.0, 0.0, f"Dati di attenuazione TC (Materiale/kVp) mancanti per {materiale} a {kvp}.", 0.0, 0.0


    data_tc_attenuation = ATTENUATION_DATA_TC[materiale][kvp]
    alpha, beta, gamma = data_tc_attenuation['alpha'], data_tc_attenuation['beta'], data_tc_attenuation['gamma']
    
    Xref_mm = calcola_spessore_x(alpha, beta, gamma, B_T)
    Xfinale_mm = max(0.0, Xref_mm - Xpre)


    log_msg = (
        f"K1sec(Head) = {K1sec_head_mGy_paz:.2e} mGy/paz (DLP={dlp_head}). "
        f"K1sec(Body) = {K1sec_body_mGy_paz:.2e} mGy/paz (DLP={dlp_body}). "
        f"$K_{{tu}}$ (a d={d}m) = {kerma_tc_non_schermato_mGy_wk:.2e} mGy/wk. "
        f"B = {B_T:.4e}. Xref={Xref_mm:.2f}mm. Xpre={Xpre:.2f}mm. (kVp: {kvp}, $K_c$: {Kc})"
    )
    
    return Xfinale_mm, kerma_tc_non_schermato_mGy_wk, log_msg, K1sec_head_mGy_paz, K1sec_body_mGy_paz


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
    # RAMO 1: DIAGNOSTICA STANDARD (Le 4 modalità definite dall'utente con Kp1)
    # -------------------------------------------------------------------------
    if tipo_immagine == "RADIOLOGIA DIAGNOSTICA" and modalita_radiografia in RAMO_1_MODES:
        
        risultati['ramo_logico'] = "RAMO 1: DIAGNOSTICA STANDARD"
        
        if tipo_barriera == "PRIMARIA":
            X_mm, K_non_schermato, log_msg = calculate_primary_thickness(params) 
            # Gestione errore se Kp1=None
            if log_msg.startswith("Dati Kp1 non definiti"):
                risultati.update({'errore': log_msg})
            else:
                 risultati.update({'spessore_finale_mm': X_mm, 'kerma_non_schermato': K_non_schermato, 'dettaglio': f"Eseguito calcolo Primario. {log_msg}"})
        
        elif tipo_barriera == "SECONDARIA":
            X_mm, X_L, X_S, K_non_schermato, log_msg = calculate_secondary_thickness(params)
            risultati.update({'spessore_finale_mm': X_mm, 'X_fuga_mm': X_L, 'X_diffusione_mm': X_S, 'kerma_non_schermato': K_non_schermato, 'dettaglio': f"Eseguito calcolo Secondario. {log_msg}"})
        
        else:
            risultati['errore'] = "Tipo di barriera non specificato per il Ramo 1."


    # -------------------------------------------------------------------------
    # RAMO 2: DIAGNOSTICA SPECIALIZZATA/GENERICA (Tutte le altre voci, inclusa TUTTE BARRIERE)
    # -------------------------------------------------------------------------
    elif tipo_immagine == "RADIOLOGIA DIAGNOSTICA" and modalita_radiografia in RAMO_2_MODES:
        
        risultati['ramo_logico'] = "RAMO 2: DIAGNOSTICA SPECIALIZZATA/GENERICA"
        
        if tipo_barriera == "PRIMARIA":
              # Queste modalità (TUTTE BARRIERE, Mammo, Angio, Fluoro) hanno Kp1=None
              X_mm, K_non_schermato, log_msg = calculate_primary_thickness(params)
              
              if log_msg.startswith("Dati Kp1 non definiti"):
                risultati['spessore_finale_mm'] = 0.0
                risultati['dettaglio'] = f"Calcolo Primario omesso per modalità specializzata/generica (Kp1 non definito). Dettaglio: {log_msg}"
              else:
                risultati.update({'spessore_finale_mm': X_mm, 'kerma_non_schermato': K_non_schermato, 'dettaglio': f"Eseguito calcolo Primario Ramo 2. {log_msg}"})

        
        elif tipo_barriera == "SECONDARIA":
            X_mm, X_L, X_S, K_non_schermato, log_msg = calculate_special_secondary_thickness(params)
            risultati.update({'spessore_finale_mm': X_mm, 'X_fuga_mm': X_L, 'X_diffusione_mm': X_S, 'kerma_non_schermato': K_non_schermato, 'dettaglio': f"Eseguito calcolo Secondario Specializzato/Generico. {log_msg}"})
        
        else:
            risultati['errore'] = "Tipo di barriera non specificato nel Ramo 2."


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
                'spessore_finale_mm': X_mm, 
                'kerma_non_schermato': K_tu, 
                'dettaglio': f"Spessore TC calcolato. {log_msg}",
                'K1sec_head_mGy_paz': K1sec_head,
                'K1sec_body_mGy_paz': K1sec_body
            })
            
        else:
            risultati['errore'] = "Tipo di barriera non specificato nel Ramo 3 (TC)."
    
    else:
        risultati['errore'] = "Combinazione Tipo Immagine/Modalità non riconosciuta."
        
    return risultati


# ====================================================================
# 5. INTERFACCIA UTENTE STREAMLIT
# ====================================================================


def main_app():
    st.set_page_config(page_title="Calcolo Schermatura NCRP 147", layout="wide")
    st.title("🛡️ Calcolo Schermatura Radiologica (NCRP 147)")
    st.caption("Implementazione della logica Ramo 1, 2 e 3 (TC).")
    
    # --- Sezione Input ---
    col1, col2, col3 = st.columns(3)
    
    # COL 1: Input Logici
    with col1:
        st.header("1. Selezione informazioni principali")
        
        tipo_immagine = st.selectbox("Tipo di Immagine", ["RADIOLOGIA DIAGNOSTICA", "TC", "Placeholder"], index=0)
        
        # Opzioni basate sul Tipo di Immagine
        if tipo_immagine == "RADIOLOGIA DIAGNOSTICA":
            # Usa tutte le chiavi di KERMA_DATA
            modalita_radiografia_options = MODALITA_RADIOGRAFIA_UI_OPTIONS
        else:
             modalita_radiografia_options = ["DLP", "Placeholder"]
            
        modalita_radiografia = st.selectbox("Modalità Radiografica", modalita_radiografia_options, index=0)
        tipo_barriera = st.selectbox("Tipo di Barriera", ["PRIMARIA", "SECONDARIA"])
        materiale_schermatura = st.selectbox("Materiale Schermatura", ["PIOMBO", "CEMENTO"])
        
        # CAMPO kVp PER TC
        kvp_tc = "N/A" # Default per non-TC
        if tipo_immagine == "TC":
            kvp_tc = st.selectbox(
                "Tensione di Picco (kVp) TC", 
                list(ATTENUATION_DATA_TC[materiale_schermatura].keys()),
                index=0
            )


    # COL 2: Input Numerici
    with col2:
        st.header("2. Dati di Esercizio")
        
        # P: Dose limite (mSv/wk)
        P_mSv_wk = st.number_input("Dose Limite (P) [mSv/settimana]", value=0.0, format="%.3f") 
        
        # T: Tasso di Occupazione [0, 1]
        tasso_occupazione_T = st.number_input("Tasso Occupazione (T) [0-1]", value=1.0, format="%.2f", min_value=0.0, max_value=1.0)
        
        # d: Distanza (m)
        distanza_d = st.number_input("Distanza dalla Sorgente (d) [metri]", value=1.0, format="%.2f", min_value=0.1)
        
        # U: Fattore di Uso [0, 1] - non usato per secondaria NCRP 147 ma incluso per primaria
        fattore_uso_U = st.number_input("Fattore di Uso (U) [0-1]", value=1.0, format="%.2f", min_value=0.0, max_value=1.0)
        
        # N: Pazienti/Settimana
        pazienti_settimana_N = st.number_input("Pazienti/Settimana (N)", value=1, min_value=1)
        
        # ====================================================================
        # CAMPI SPECIFICI TC (RAMO 3)
        # ====================================================================
        weekly_n_head = 0
        weekly_n_body = 0
        contrast_factor = 1.0
        
        if tipo_immagine == "TC":
            st.markdown("---") 
            st.subheader("Ripartizione Esami Settimanali (N)")
            
            weekly_n_head = st.number_input(
                "WEEKLY N HEAD PROCED", 
                value=0, 
                min_value=0, 
                help="Numero di procedure TC di Testa a settimana."
            )
            
            weekly_n_body = st.number_input(
                "WEEKLY N BODY PROCED", 
                value=0, 
                min_value=0, 
                help="Numero di procedure TC di Corpo a settimana."
            )

            contrast_factor = st.number_input(
                "CONTRAST Factor ($K_c$)", 
                value=1.0, 
                min_value=1.0, 
                max_value=2.0, 
                format="%.1f",
                help="Fattore moltiplicativo per il Kerma dovuto all'uso di Mezzo di Contrasto (1.4 tipico)."
            )


        st.markdown("---") 
        
        # LOGICA DINAMICA PER LA SELEZIONE X-PRE
        # *** LOGICA AGGIORNATA PER STANZA RADIOGRAFICA (CHEST BUCKY) ***
        if modalita_radiografia == "STANZA RADIOGRAFICA (CHEST BUCKY)" or modalita_radiografia == "STANZA RADIOGRAFICA TORACE(CHEST ROOM)":
            # Per CHEST BUCKY e CHEST ROOM, usa Table/Holder come richiesto.
            options_x_pre = X_PRE_TABLE_HOLDER_KEYS
            default_index = options_x_pre.index("PIOMBO (0.85 mm) - Table/Holder") if "PIOMBO (0.85 mm) - Table/Holder" in options_x_pre else 0
            help_text = "Schermatura intrinseca del ricevitore immagine (Table/Holder)."
        else:
            # Tutte le altre modalità/TC, usiamo le opzioni Table/Holder come default.
            # Nota: se l'intento è usare Cross-Table per CHEST BUCKY, la condizione deve essere modificata.
            options_x_pre = X_PRE_TABLE_HOLDER_KEYS
            default_index = options_x_pre.index("PIOMBO (0.85 mm) - Table/Holder") if "PIOMBO (0.85 mm) - Table/Holder" in options_x_pre else 0
            help_text = "Schermatura intrinseca del ricevitore immagine (Table/Holder, o NESSUNO se non applicabile)."
            
            # Nota: Questa else-block ora copre tutte le modalità tranne CHEST BUCKY e CHEST ROOM, ma usa gli stessi Table/Holder keys.
            # Se in futuro si desidera usare Cross-Table per altre modalità, la logica andrà perfezionata.

        
        # Selectbox dinamico:
        X_PRE_selection_key = st.selectbox(
            "Schermatura Pre-esistente ($X_{pre}$) [mm]", 
            options=options_x_pre,
            index=default_index, 
            help=help_text + " (Vedere Tabella 4.6 NCRP 147)."
        )
        
        # Ottieni il valore numerico (mm) dalla selezione
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
            # AGGIUNTA DEI PARAMETRI TC (Cruciale per RAMO 3)
            'weekly_n_head': weekly_n_head,
            'weekly_n_body': weekly_n_body,
            'contrast_factor': contrast_factor,
            'kvp_tc': kvp_tc
        }
        
        if st.button("🟡 ESEGUI CALCOLO SCHERMATURA", type="primary"):
            # Resetta lo stato di esecuzione per forzare l'aggiornamento
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
            
            # Display dei risultati principali
            col_res1, col_res2, col_res3 = st.columns(3)
            col_res1.metric("Spessore Finale Richiesto (X)", f"**{results['spessore_finale_mm']:.2f} mm** {params['materiale_schermatura']}")
            col_res2.metric("Kerma Non Schermato ($K_{tu}$)", f"{results.get('kerma_non_schermato', 0.0):.2e} mGy/settimana")
            col_res3.metric("Fattore di Trasmittanza (B)", f"{params['P_mSv_wk'] / (results.get('kerma_non_schermato', 1.0) * params['tasso_occupazione_T']):.4e}" if results.get('kerma_non_schermato', 1.0) * params['tasso_occupazione_T'] > 0 else "N/A")
            
            # Display dettagli secondari
            st.subheader("Dettagli del Processo")
            
            if results['ramo_logico'] == 'RAMO 3: TC (Calcolo Spessore)':
                  st.info(results['dettaglio'])
                  st.markdown("**Valori di Kerma $K_{1sec}$ calcolati (a 1 metro):**")
                  st.write(f"- $K_{{1sec}}(\\text{{Head}})$: {results.get('K1sec_head_mGy_paz', 0.0):.2e} mGy/paziente (DLP fisso: {DLP_TC_FIXED_VALUES['HEAD']} mGy·cm)")
                  st.write(f"- $K_{{1sec}}(\\text{{Body}})$: {results.get('K1sec_body_mGy_paz', 0.0):.2e} mGy/paziente (DLP fisso: {DLP_TC_FIXED_VALUES['BODY']} mGy·cm)")
                  st.markdown("**Parametri TC utilizzati:**")
                  st.write(f"- $K_c$ (Fattore Contrasto): {params['contrast_factor']:.1f}")
                  st.write(f"- N Testa/settimana: {params['weekly_n_head']}")
                  st.write(f"- N Corpo/settimana: {params['weekly_n_body']}")
                  st.write(f"- $X_{{pre}}$ (Pre-schermatura): {params['X_PRE_mm']:.2f} mm (Selezionato: {X_PRE_selection_key})")
              
            else: # Ramo 1 e 2
                st.info(results['dettaglio'])
                
                # Ottiene la chiave NCRP utilizzata per l'attenuazione (per display)
                ncrp_key_used = params['modalita_radiografia']
                
                # Ottiene il valore Kp1 o Ksec1 combinato usato per il calcolo.
                K_val = KERMA_DATA.get(ncrp_key_used, {}).get('Kp1', KERMA_DATA.get(ncrp_key_used, {}).get('Ksec1_Comb', 'N/A'))
                
                st.markdown(f"**Parametri di Input:**")
                st.write(f"- Modalità NCRP (Chiave Dati): {ncrp_key_used}")
                st.write(f"- $K_{{val}}$ (NCRP 147): {K_val}")
                st.write(f"- $X_{{pre}}$ (Pre-schermatura): {params['X_PRE_mm']:.2f} mm (Selezionato: {X_PRE_selection_key})")
                
                if params['tipo_barriera'] == "SECONDARIA":
                    st.markdown("**Componenti Secondarie (Modello $K_{s1}$ Combinato):**")
                    st.write(f"- Spessore Fuga ($X_L$): {results.get('X_fuga_mm', 0.0):.2f} mm")
                    st.write(f"- Spessore Diffusione ($X_S$): {results.get('X_diffusione_mm', 0.0):.2f} mm")
                
if __name__ == "__main__":
    if 'run' not in st.session_state:
        st.session_state['run'] = False
    if 'results' not in st.session_state:
        st.session_state['results'] = None
        
    main_app()