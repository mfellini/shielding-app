import streamlit as st
import math

# ====================================================================
# 1. DATI NCRP 147 CONSOLIDATI
# ====================================================================

# Kp1: Kerma primario non schermato a 1m per paziente [mGy/paziente] (Tabella 4.5)
KERMA_KP1 = {
    # Mappatura delle scelte del frontend alle righe della Tabella 4.5
    "STANZA RADIOGRAFICA": 5.2,          # Rad Room (floor or other barriers)
    "RADIOGRAFIA TORACE": 1.2,           # Chest Room
    "FLUOROSCOPIA": 5.9,                 # Rad Tube (R&F Room)
    
    # Dati Specializzati (usiamo valori da Tabella 4.5/4.7 se non specifici)
    "MAMMOGRAFIA": 0.0,                  # La Mammografia è trattata solo come Secondaria nel Ramo 2 (con Ks1)
    "ANGIO CARDIACA": 5.9,               # Placeholder
    "ANGIO PERIFERICA": 5.9,             # Placeholder
    "ANGIO NEURO": 5.9                   # Placeholder
}

# Ks1: Kerma secondario non schermato a 1m per paziente [mGy/paziente] (Tabella 4.7)
KERMA_KS1 = {
    # Mappatura dalle scelte del frontend
    "STANZA RADIOGRAFICA": 0.21,         # Rad Room (all barriers)
    "RADIOGRAFIA TORACE": 0.09,          # Chest Room
    "FLUOROSCOPIA": 0.21,                # R&F Tube (R&F Room)
    
    # Dati Specializzati (Esempi da Tabella 4.7, Angio/Mammo)
    "MAMMOGRAFIA": 0.015,                # Esempio
    "ANGIO CARDIACA": 0.70,              # Esempio
    "ANGIO PERIFERICA": 0.70,
    "ANGIO NEURO": 0.70
}

# Parametri di Fitting (Alfa, Beta, Gamma) per Barriera Primaria (Tabella B.1)
ATTENUATION_DATA_PRIMARY = {
    "STANZA RADIOGRAFICA": {
        "PIOMBO": {'alpha': 2.651, 'beta': 1.656e+01, 'gamma': 4.585e-01}, # Rad Room floor...
        "CEMENTO": {'alpha': 3.994e-02, 'beta': 1.448e+02, 'gamma': 4.231e-01} #
    },
    "RADIOGRAFIA TORACE": {
        "PIOMBO": {'alpha': 2.283, 'beta': 1.074e+01, 'gamma': 6.370e-01}, # Chest Room
        "CEMENTO": {'alpha': 3.622e-02, 'beta': 7.766e+01, 'gamma': 5.404e-01} #
    },
    "FLUOROSCOPIA": {
        "PIOMBO": {'alpha': 2.295, 'beta': 1.300e+01, 'gamma': 5.573e-01}, # Rad Tube R&F
        "CEMENTO": {'alpha': 3.549e-02, 'beta': 1.164e+02, 'gamma': 5.774e-01} #
    },
    # Dati Specializzati (usati se per errore si chiede Primaria in Ramo 2)
    "MAMMOGRAFIA": {
        "PIOMBO": {'alpha': 3.060e+01, 'beta': 1.776e+02, 'gamma': 3.308e-01}, # Mammography Room
        "CEMENTO": {'alpha': 2.577e-01, 'beta': 1.765e+00, 'gamma': 3.644e-01} #
    },
    "ANGIO CARDIACA": {
        "PIOMBO": {'alpha': 2.389, 'beta': 1.426e+01, 'gamma': 5.948e-01}, # Cardiac Angiography
        "CEMENTO": {'alpha': 3.717e-02, 'beta': 1.087e+02, 'gamma': 4.879e-01} #
    },
    "ANGIO PERIFERICA": {
        "PIOMBO": {'alpha': 2.728, 'beta': 1.852e+01, 'gamma': 4.614e-01}, # Peripheral Angiography
        "CEMENTO": {'alpha': 4.292e-02, 'beta': 1.538e+02, 'gamma': 4.236e-01} #
    }
}

# Parametri di Fitting (Alfa, Beta, Gamma) per Barriera Secondaria (Tabella C.1)
ATTENUATION_DATA_SECONDARY = {
    "STANZA RADIOGRAFICA": {
        "PIOMBO": {'alpha': 2.454, 'beta': 1.350e+01, 'gamma': 5.679e-01}, # Rad Room (all barriers)
        "CEMENTO": {'alpha': 3.829e-02, 'beta': 1.341e+02, 'gamma': 4.416e-01} #
    },
    "RADIOGRAFIA TORACE": {
        "PIOMBO": {'alpha': 2.417, 'beta': 1.056e+01, 'gamma': 6.002e-01}, # Chest Room
        "CEMENTO": {'alpha': 3.882e-02, 'beta': 7.766e+01, 'gamma': 5.404e-01} #
    },
    "FLUOROSCOPIA": {
        "PIOMBO": {'alpha': 2.454, 'beta': 1.350e+01, 'gamma': 5.679e-01}, # Rad Room (all barriers)
        "CEMENTO": {'alpha': 3.829e-02, 'beta': 1.341e+02, 'gamma': 4.416e-01} #
    },
    # Dati Specializzati (Tabella C.1)
    "MAMMOGRAFIA": {
        "PIOMBO": {'alpha': 3.100e+00, 'beta': 1.800e+01, 'gamma': 3.400e-01},
        "CEMENTO": {'alpha': 3.000e-02, 'beta': 2.000e+02, 'gamma': 3.800e-01}
    },
    "ANGIO CARDIACA": {
        "PIOMBO": {'alpha': 2.410e+00, 'beta': 1.400e+01, 'gamma': 5.800e-01},
        "CEMENTO": {'alpha': 3.900e-02, 'beta': 1.300e+02, 'gamma': 4.300e-01}
    },
    "ANGIO PERIFERICA": {
        "PIOMBO": {'alpha': 2.700e+00, 'beta': 1.800e+01, 'gamma': 4.600e-01},
        "CEMENTO": {'alpha': 4.300e-02, 'beta': 1.540e+02, 'gamma': 4.240e-01}
    },
    "ANGIO NEURO": { # Riuso Angio Cardiaca come fallback
        "PIOMBO": {'alpha': 2.410e+00, 'beta': 1.400e+01, 'gamma': 5.800e-01},
        "CEMENTO": {'alpha': 3.900e-02, 'beta': 1.300e+02, 'gamma': 4.300e-01}
    }
}

# NUOVI DIZIONARI PER TC (RAMO 3) - Basati su kVp
# TABELLA A.2 (Piombo) e A.3 (Cemento) NCRP 147
ATTENUATION_DATA_TC = {
    "PIOMBO": {
        "120 kVp": {'alpha': 2.246, 'beta': 5.73, 'gamma': 0.547},
        "140 kVp": {'alpha': 2.009, 'beta': 3.99, 'gamma': 0.342}
    },
    "CEMENTO": {
        "120 kVp": {'alpha': 0.0383, 'beta': 0.0142, 'gamma': 0.658},
        "140 kVp": {'alpha': 0.0336, 'beta': 0.0122, 'gamma': 0.519}
    }
}

# NUOVO DIZIONARIO PER LE SCELTE DELL'UTENTE (PRESHIELDING_XPRE_OPTIONS)
# Spessore di Preshielding (Xpre) in mm (Tabella 4.6 - Image receptor in table/holder)
PRESHIELDING_XPRE_OPTIONS = {
    "NESSUNO (0.0 mm)": 0.0,
    "PIOMBO (0.85 mm)": 0.85, # Valore standard per Pb (NCRP 147 Tabella 4.6)
    "CEMENTO (72.0 mm)": 72.0, # Valore standard per Cemento (NCRP 147 Tabella 4.6)
    "ACCIAIO (7.0 mm)": 7.0   # Valore standard per Acciaio (NCRP 147 Tabella 4.6)
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
        
        numeratore_ln = B**(-gamma) + (beta / alpha)
        denominatore_ln = 1 + (beta / alpha)
        
        if numeratore_ln <= 0 or denominatore_ln <= 0:
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
        # U non è usato nel calcolo Primario del Ramo 1, ma lo includiamo qui per flessibilità.
        kerma = (K_val * U * N) / (d ** 2)
        return kerma
    except Exception:
        return 0.0

# ====================================================================
# 3. FUNZIONI DI CALCOLO SPECIFICHE (RAMO 1 & 2)
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

    Kp1 = KERMA_KP1.get(modalita, 0.0) 
    
    if modalita not in ATTENUATION_DATA_PRIMARY or materiale not in ATTENUATION_DATA_PRIMARY[modalita]:
        return 0.0, 0.0, "Dati di attenuazione Primaria mancanti."
        
    data = ATTENUATION_DATA_PRIMARY[modalita][materiale]
    alpha, beta, gamma = data['alpha'], data['beta'], data['gamma']
    
    # 1. Kerma non schermato (incidente)
    kerma_non_schermato_mGy_wk = calcola_kerma_incidente(Kp1, U, N, d)
    
    if kerma_non_schermato_mGy_wk * T == 0:
        return 0.0, 0.0, "Kerma o Tasso di Occupazione (T) nullo."
        
    # 2. Fattore di Trasmittanza B
    B_P = P / (kerma_non_schermato_mGy_wk * T)
    
    # 3. Spessore di Riferimento Xref
    Xref_mm = calcola_spessore_x(alpha, beta, gamma, B_P)
    
    # 4. Spessore Finale (Xref - Xpre)
    Xfinale_mm = max(0.0, Xref_mm - Xpre)
    
    log_msg = f"Kp1={Kp1:.2f}. B={B_P:.4e}. Xref={Xref_mm:.2f}mm. Xpre={Xpre:.2f}mm."
    return Xfinale_mm, kerma_non_schermato_mGy_wk, log_msg

def calculate_secondary_thickness(params):
    """ Implementa il calcolo Secondario (Ramo 1). """
    P = params.get('P_mSv_wk', 0.0) 
    T = params.get('tasso_occupazione_T', 1.0)
    d = params.get('distanza_d', 2.0)
    U = params.get('fattore_uso_U', 1.0) # U è tipicamente 1 per la secondaria
    N = params.get('pazienti_settimana_N', 100)
    modalita = params.get('modalita_radiografia')
    materiale = params.get('materiale_schermatura')
    Xpre = params.get('X_PRE_mm', 0.0) 

    Ks1 = KERMA_KS1.get(modalita, 0.0) 
    
    if modalita not in ATTENUATION_DATA_SECONDARY or materiale not in ATTENUATION_DATA_SECONDARY[modalita]:
        return 0.0, 0.0, 0.0, 0.0, "Dati di attenuazione Secondaria mancanti."
        
    data = ATTENUATION_DATA_SECONDARY[modalita][materiale]
    alpha, beta, gamma = data['alpha'], data['beta'], data['gamma']
    
    # 1. Kerma non schermato (incidente)
    kerma_non_schermato_mGy_wk = calcola_kerma_incidente(Ks1, U, N, d)
    
    if kerma_non_schermato_mGy_wk * T == 0:
        return 0.0, 0.0, 0.0, 0.0, "Kerma o Tasso di Occupazione (T) nullo."
        
    # 2. Fattore di Trasmittanza B
    B_S = P / (kerma_non_schermato_mGy_wk * T)
    
    # 3. Spessore di Riferimento Xref
    Xref_mm = calcola_spessore_x(alpha, beta, gamma, B_S)
    
    # 4. Spessore Finale (Xref - Xpre)
    Xfinale_mm = max(0.0, Xref_mm - Xpre)
    
    log_msg = f"Ks1={Ks1:.2f}. B={B_S:.4e}. Xref={Xref_mm:.2f}mm. Xpre={Xpre:.2f}mm. (Modello combinato Ks1)"
    
    # Nel modello combinato Ks1, X_L = X_S = X_finale
    return Xfinale_mm, Xfinale_mm, Xfinale_mm, kerma_non_schermato_mGy_wk, log_msg

def calculate_special_secondary_thickness(params):
    """ Implementa il calcolo Secondario (Ramo 2). Stesso flusso logico di Ramo 1."""
    return calculate_secondary_thickness(params)

def calculate_tc_thickness(params):
    """ 
    Implementa il calcolo Secondario (Ramo 3 - TC).
    Utilizza i DLP fissi (1200 mGy*cm per Head, 550 mGy*cm per Body) per calcolare il Kerma K1sec.
    """
    P = params.get('P_mSv_wk', 0.0) 
    T = params.get('tasso_occupazione_T', 1.0)
    d = params.get('distanza_d', 2.0)
    materiale = params.get('materiale_schermatura')
    Xpre = params.get('X_PRE_mm', 0.0)
    
    # Parametri specifici TC (Recuperati da params)
    N_head = params.get('weekly_n_head', 0) 
    N_body = params.get('weekly_n_body', 0)
    Kc = params.get('contrast_factor', 1.0) # Fattore di Contrasto
    kvp = params.get('kvp_tc')
    
    # --- 1. Calcolo del Kerma non schermato a 1m per paziente (K1sec) ---
    # K1sec(head) = khead * DLP_head * Kc
    dlp_head = DLP_TC_FIXED_VALUES["HEAD"]
    K1sec_head_mGy_paz = K_HEAD_DIFF * dlp_head * Kc
    
    # K1sec(body) = 1.2 * kbody * DLP_body * Kc
    dlp_body = DLP_TC_FIXED_VALUES["BODY"]
    K1sec_body_mGy_paz = 1.2 * K_BODY_DIFF * dlp_body * Kc 
    
    # --- 2. Calcolo del Kerma non schermato totale settimanale alla distanza d ($K_{tu}$) ---
    total_kerma_at_1m_mGy_wk = (K1sec_head_mGy_paz * N_head) + (K1sec_body_mGy_paz * N_body)
    
    if d <= 0:
        kerma_tc_non_schermato_mGy_wk = 0.0
    else:
        # $K_{tu}$ (Kerma Settimanale alla distanza d)
        kerma_tc_non_schermato_mGy_wk = (1 / (d ** 2)) * total_kerma_at_1m_mGy_wk
    
    # --- 3. Calcolo del Fattore di Trasmittanza B ($B_{T}$) ---
    if kerma_tc_non_schermato_mGy_wk * T <= 0:
        B_T = 1.0 
    else:
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
    # RAMO 1: DIAGNOSTICA STANDARD (Stanza, Torace, Fluoroscopia)
    # -------------------------------------------------------------------------
    if tipo_immagine == "RADIOLOGIA DIAGNOSTICA" and \
       modalita_radiografia in ["STANZA RADIOGRAFICA", "RADIOGRAFIA TORACE", "FLUOROSCOPIA"]:
        
        risultati['ramo_logico'] = "RAMO 1: DIAGNOSTICA STANDARD"
        
        if tipo_barriera == "PRIMARIA":
            X_mm, K_non_schermato, log_msg = calculate_primary_thickness(params) 
            risultati.update({'spessore_finale_mm': X_mm, 'kerma_non_schermato': K_non_schermato, 'dettaglio': f"Eseguito calcolo Primario. {log_msg}"})
        
        elif tipo_barriera == "SECONDARIA":
            X_mm, X_L, X_S, K_non_schermato, log_msg = calculate_secondary_thickness(params)
            risultati.update({'spessore_finale_mm': X_mm, 'X_fuga_mm': X_L, 'X_diffusione_mm': X_S, 'kerma_non_schermato': K_non_schermato, 'dettaglio': f"Eseguito calcolo Secondario. {log_msg}"})
        
        else:
            risultati['errore'] = "Tipo di barriera non specificato per il Ramo 1."

    # -------------------------------------------------------------------------
    # RAMO 2: DIAGNOSTICA SPECIALIZZATA (Mammo, Angio)
    # -------------------------------------------------------------------------
    elif tipo_immagine == "RADIOLOGIA DIAGNOSTICA" and \
          modalita_radiografia in ["MAMMOGRAFIA", "ANGIO CARDIACA", "ANGIO PERIFERICA", "ANGIO NEURO"]:
        
        risultati['ramo_logico'] = "RAMO 2: DIAGNOSTICA SPECIALIZZATA"
        
        if tipo_barriera == "PRIMARIA":
             risultati['spessore_finale_mm'] = 0.0
             risultati['dettaglio'] = "Calcolo Primario omesso (già gestito da detettore/apparecchio)."
        
        elif tipo_barriera == "SECONDARIA":
            X_mm, X_L, X_S, K_non_schermato, log_msg = calculate_special_secondary_thickness(params)
            risultati.update({'spessore_finale_mm': X_mm, 'X_fuga_mm': X_L, 'X_diffusione_mm': X_S, 'kerma_non_schermato': K_non_schermato, 'dettaglio': f"Eseguito calcolo Secondario Specializzato. {log_msg}"})
        
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
    return risultati

# ====================================================================
# 5. INTERFACCIA UTENTE STREAMLIT
# ====================================================================

def main_app():
    st.set_page_config(page_title="Calcolo Schermatura NCRP 147", layout="wide")
    st.title("Calcolo Schermatura Radiologica (NCRP 147)")
    st.caption("Implementazione della logica Ramo 1, 2 e 3 (TC).")
    
    # --- Sezione Input ---
    col1, col2, col3 = st.columns(3)
    
    # COL 1: Input Logici
    with col1:
        st.header("1. Selezione informazioni principali")
        
        tipo_immagine = st.selectbox("Tipo di Immagine", ["RADIOLOGIA DIAGNOSTICA", "TC", "Placeholder"], index=0)
        
        # Opzioni basate sul Tipo di Immagine
        if tipo_immagine == "RADIOLOGIA DIAGNOSTICA":
            modalita_radiografia_options = ["STANZA RADIOGRAFICA", "RADIOGRAFIA TORACE", "FLUOROSCOPIA", 
                                             "MAMMOGRAFIA", "ANGIO CARDIACA", "ANGIO PERIFERICA", "ANGIO NEURO", "R&F"]
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
        P_mSv_wk = st.number_input("Dose Limite (P) [mSv/settimana]", value=0.00, format="%.3f") 
        
        # T: Tasso di Occupazione [0, 1]
        tasso_occupazione_T = st.number_input("Tasso Occupazione (T) [0-1]", value=1.0, format="%.2f", min_value=0.0, max_value=1.0)
        
        # d: Distanza (m)
        distanza_d = st.number_input("Distanza dalla Sorgente (d) [metri]", value=1.0, format="%.2f", min_value=0.1)
        
        # U: Fattore di Uso [0, 1]
        fattore_uso_U = st.number_input("Fattore di Uso (U) [0-1]", value=1.0, format="%.2f", min_value=0.0, max_value=1.0)
        
        # N: Pazienti/Settimana
        pazienti_settimana_N = st.number_input("Pazienti/Settimana (N)", value=100, min_value=1)
        
        # ====================================================================
        # CAMPI SPECIFICI TC (RAMO 3)
        # ====================================================================
        weekly_n_head = 0
        weekly_n_body = 0
        contrast_factor = 1.0
        
        if tipo_immagine == "TC":
            st.markdown("---") 
            st.subheader("Parametri di Calcolo Kerma TC")
            
            # Mostra i DLP fissi utilizzati (non modificabili)
            st.write(f"DLP Head (Fisso, Tab. 5.2): **{DLP_TC_FIXED_VALUES['HEAD']}** mGy·cm")
            st.write(f"DLP Body (Fisso, Tab. 5.2): **{DLP_TC_FIXED_VALUES['BODY']}** mGy·cm")
            
            st.subheader("Ripartizione Esami Settimanali (N)")
            
            weekly_n_head = st.number_input(
                "WEEKLY N HEAD PROCED", 
                value=40, 
                min_value=0, 
                help="Numero di procedure TC di Testa a settimana."
            )
            
            weekly_n_body = st.number_input(
                "WEEKLY N BODY PROCED", 
                value=60, 
                min_value=0, 
                help="Numero di procedure TC di Corpo a settimana."
            )

            contrast_factor = st.number_input(
                "CONTRAST Factor ($K_c$)", 
                value=1.4, 
                min_value=1.0, 
                max_value=2.0, 
                format="%.1f",
                help="Fattore moltiplicativo per il Kerma dovuto all'uso di Mezzo di Contrasto."
            )

        st.markdown("---") 
        
        # NUOVO CAMPO X-PRE (SELECTBOX)
        X_PRE_selection = st.selectbox(
            "Schermatura X-PRE [mm]", 
            options=list(PRESHIELDING_XPRE_OPTIONS.keys()),
            index=0, 
            help="Schermatura intrinseca del sistema di ricezione dell'immagine (NCRP 147)."
        )
        
        # Ottieni il valore numerico (mm) dalla selezione
        X_PRE_value = PRESHIELDING_XPRE_OPTIONS[X_PRE_selection]

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
            # Eliminati dlp_mGy_cm e ctdivol_mGy dai parametri passati
        }
        
        if st.button("🟡 ESEGUI CALCOLO SCHERMATURA", type="primary"):
            if 'results' not in st.session_state:
                st.session_state['results'] = None
            if 'run' not in st.session_state:
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
            st.error(f"Errore Logico/Implementazione: {results['errore']}")
        else:
            st.success(f"Calcolo Eseguito: {results['ramo_logico']}")
            
            # Display dei risultati principali
            col_res1, col_res2, col_res3 = st.columns(3)
            col_res1.metric("Spessore Finale Richiesto (X)", f"{results['spessore_finale_mm']:.2f} mm {params['materiale_schermatura']}")
            col_res2.metric("Kerma Non Schermato (alla distanza d)", f"{results.get('kerma_non_schermato', 0.0):.2f} mGy/settimana")
            col_res3.metric("Fattore di Uso (U) Utilizzato", f"{params['fattore_uso_U']:.2f}")
            
            # Display dettagli secondari
            if results['ramo_logico'] == 'RAMO 3: TC (Calcolo Spessore)':
                 st.subheader("Dettagli del Processo")
                 st.info(results['dettaglio'])
                 st.markdown("**Valori di Kerma $K_{1sec}$ calcolati (a 1 metro):**")
                 st.write(f"- $K_{{1sec}}(\\text{{Head}})$: {results.get('K1sec_head_mGy_paz', 0.0):.2e} mGy/paziente (DLP fisso: {DLP_TC_FIXED_VALUES['HEAD']} mGy·cm)")
                 st.write(f"- $K_{{1sec}}(\\text{{Body}})$: {results.get('K1sec_body_mGy_paz', 0.0):.2e} mGy/paziente (DLP fisso: {DLP_TC_FIXED_VALUES['BODY']} mGy·cm)")
                 st.markdown("**Parametri TC utilizzati:**")
                 st.write(f"- $K_c$ (Fattore Contrasto): {params['contrast_factor']:.1f}")
                 st.write(f"- N Testa/settimana: {params['weekly_n_head']}")
                 st.write(f"- N Corpo/settimana: {params['weekly_n_body']}")
                 st.write(f"- $X_{{pre}}$ (Pre-schermatura): {params['X_PRE_mm']:.2f} mm")
            
            else: # Ramo 1 e 2
                st.subheader("Dettagli del Processo")
                st.info(results['dettaglio'])
                
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