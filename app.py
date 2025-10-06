import streamlit as st
import math

# ====================================================================
# 1. DATI NCRP 147 CONSOLIDATI
# ====================================================================

# [cite_start]Kp1: Kerma primario non schermato a 1m per paziente [mGy/paziente] (Tabella 4.5) [cite: 1]
KERMA_KP1 = {
    # Mappatura delle scelte del frontend alle righe della Tabella 4.5
    "STANZA RADIOGRAFICA": 5.2,          # Rad Room (floor or other barriers) [cite: 1]
    "RADIOGRAFIA TORACE": 1.2,           # Chest Room [cite: 1]
    "FLUOROSCOPIA": 5.9,                 # Rad Tube (R&F Room) [cite: 1]
    
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

# [cite_start]Parametri di Fitting (Alfa, Beta, Gamma) per Barriera Primaria (Tabella B.1) [cite: 2]
ATTENUATION_DATA_PRIMARY = {
    "STANZA RADIOGRAFICA": {
        "PIOMBO": {'alpha': 2.651, 'beta': 1.656e+01, 'gamma': 4.585e-01}, # Rad Room floor... [cite: 2]
        "CEMENTO": {'alpha': 3.994e-02, 'beta': 1.448e+02, 'gamma': 4.231e-01} # [cite: 2]
    },
    "RADIOGRAFIA TORACE": {
        "PIOMBO": {'alpha': 2.283, 'beta': 1.074e+01, 'gamma': 6.370e-01}, # Chest Room [cite: 2]
        "CEMENTO": {'alpha': 3.622e-02, 'beta': 7.766e+01, 'gamma': 5.404e-01} # [cite: 2]
    },
    "FLUOROSCOPIA": {
        "PIOMBO": {'alpha': 2.295, 'beta': 1.300e+01, 'gamma': 5.573e-01}, # Rad Tube R&F [cite: 2]
        "CEMENTO": {'alpha': 3.549e-02, 'beta': 1.164e+02, 'gamma': 5.774e-01} # [cite: 2]
    },
    # Dati Specializzati (usati se per errore si chiede Primaria in Ramo 2)
    "MAMMOGRAFIA": {
        "PIOMBO": {'alpha': 3.060e+01, 'beta': 1.776e+02, 'gamma': 3.308e-01}, # Mammography Room [cite: 2]
        "CEMENTO": {'alpha': 2.577e-01, 'beta': 1.765e+00, 'gamma': 3.644e-01} # [cite: 2]
    },
    "ANGIO CARDIACA": {
        "PIOMBO": {'alpha': 2.389, 'beta': 1.426e+01, 'gamma': 5.948e-01}, # Cardiac Angiography [cite: 2]
        "CEMENTO": {'alpha': 3.717e-02, 'beta': 1.087e+02, 'gamma': 4.879e-01} # [cite: 2]
    },
    "ANGIO PERIFERICA": {
        "PIOMBO": {'alpha': 2.728, 'beta': 1.852e+01, 'gamma': 4.614e-01}, # Peripheral Angiography [cite: 2]
        "CEMENTO": {'alpha': 4.292e-02, 'beta': 1.538e+02, 'gamma': 4.236e-01} # [cite: 2]
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

# NUOVO DIZIONARIO PER LE SCELTE DELL'UTENTE (PRESHIELDING_XPRE_OPTIONS)
# [cite_start]Spessore di Preshielding (Xpre) in mm (Tabella 4.6 - Image receptor in table/holder) [cite: 3]
PRESHIELDING_XPRE_OPTIONS = {
    "NESSUNO (0.0 mm)": 0.0,
    "PIOMBO (0.85 mm)": 0.85, # Valore standard per Pb (NCRP 147 Tabella 4.6)
    "CEMENTO (72.0 mm)": 72.0, # Valore standard per Cemento (NCRP 147 Tabella 4.6)
    "ACCIAIO (7.0 mm)": 7.0  # Valore standard per Acciaio (NCRP 147 Tabella 4.6)
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
    # RECUPERO X-PRE DALL'INPUT DELL'UTENTE
    Xpre = params.get('X_PRE_mm', 0.0) 

    Kp1 = KERMA_KP1.get(modalita, 0.0) 
    
    if modalita not in ATTENUATION_DATA_PRIMARY or materiale not in ATTENUATION_DATA_PRIMARY[modalita]:
        return 0.0, 0.0, "Dati di attenuazione Primaria mancanti."
        
    data = ATTENUATION_DATA_PRIMARY[modalita][materiale]
    # RIMOZIONE DELLA RIGA Xpre = PRESHIELDING_XPRE.get(materiale, 0.0)
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
    # RECUPERO X-PRE DALL'INPUT DELL'UTENTE
    Xpre = params.get('X_PRE_mm', 0.0) 

    Ks1 = KERMA_KS1.get(modalita, 0.0) 
    
    if modalita not in ATTENUATION_DATA_SECONDARY or materiale not in ATTENUATION_DATA_SECONDARY[modalita]:
        return 0.0, 0.0, 0.0, 0.0, "Dati di attenuazione Secondaria mancanti."
        
    data = ATTENUATION_DATA_SECONDARY[modalita][materiale]
    # RIMOZIONE DELLA RIGA Xpre = PRESHIELDING_XPRE.get(materiale, 0.0)
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
    # Riutilizzo del codice di calculate_secondary_thickness, che è identico nel flusso.
    # L'unica differenza è che usa dati NCRP diversi per Mammografia/Angio (Tab C.1).
    return calculate_secondary_thickness(params)

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
    # RAMO 3 (TC) e RAMO 4 (R&F) - PLACEHOLDER
    # -------------------------------------------------------------------------
    elif tipo_immagine == "TC" and modalita_radiografia == "DLP":
         risultati.update({'ramo_logico': 'RAMO 3: TC (Placeholder)', 'errore': 'Logica TC (DLP) non ancora implementata.'})
         
    elif tipo_immagine == "RADIOLOGIA DIAGNOSTICA" and modalita_radiografia == "R&F":
         risultati.update({'ramo_logico': 'RAMO 4: R&F (Placeholder)', 'errore': 'Logica R&F non ancora implementata.'})
    
    else:
        risultati['errore'] = "Combinazione di 'Tipo Immagine' e 'Modalità Radiografia' non prevista nel flusso logico."
        
    return risultati

# ====================================================================
# 5. INTERFACCIA UTENTE STREAMLIT
# ====================================================================

def main_app():
    st.set_page_config(page_title="Calcolo Schermatura NCRP 147", layout="wide")
    st.title("Calcolo Schermatura Radiologica (NCRP 147)")
    st.caption("Implementazione della logica Ramo 1 e Ramo 2.")
    
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
        
        st.markdown("---") # Separatore visivo
        
        # NUOVO CAMPO X-PRE (SELECTBOX)
        X_PRE_selection = st.selectbox(
            "Schermatura X-PRE [mm]", 
            options=list(PRESHIELDING_XPRE_OPTIONS.keys()),
            index=0, # Imposta "NESSUNO (0.0 mm)" come default
            help="Schermatura intrinseca del sistema di ricezione dell'immagine (NCRP 147). Selezionare 0.0 mm se non applicabile."
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
            # AGGIUNGI X-PRE VALORE NUMERICO
            'X_PRE_mm': X_PRE_value 
        }
        
        if st.button("🟡 ESEGUI CALCOLO SCHERMATURA", type="primary"):
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
            
            # Display dettagli secondari (se disponibili)
            if results['ramo_logico'] in ["RAMO 1: DIAGNOSTICA STANDARD", "RAMO 2: DIAGNOSTICA SPECIALIZZATA"]:
                st.subheader("Dettagli del Processo")
                st.info(results['dettaglio'])
                
                if params['tipo_barriera'] == "SECONDARIA":
                    st.markdown("**Componenti Secondarie (Modello Ks1 Combinato):**")
                    st.write(f"- Spessore Fuga (X_L): {results.get('X_fuga_mm', 0.0):.2f} mm")
                    st.write(f"- Spessore Diffusione (X_S): {results.get('X_diffusione_mm', 0.0):.2f} mm")
if __name__ == "__main__":
   main_app()