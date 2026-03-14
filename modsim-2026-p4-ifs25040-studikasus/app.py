import numpy as np
from scipy.integrate import solve_ivp
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from dataclasses import dataclass, field
import datetime
import time

# ====================
# 1. KONFIGURASI SISTEM
# ====================

@dataclass
class WaterTankConfig:
    radius: float = 1.0           
    max_height: float = 5.0       
    inlet_flow_rate: float = 0.05  # m³/s
    outlet_pipe_radius: float = 0.05 
    discharge_coeff: float = 0.6   
    initial_level: float = 0.0     
    simulation_time: float = 60.0  # menit
    
    @property
    def tank_area(self):
        return np.pi * (self.radius ** 2)

# ====================
# 2. ENGINE SIMULASI
# ====================

class WaterPhysicsModel:
    def __init__(self, config: WaterTankConfig):
        self.config = config
        self.g = 9.81

    def system_dynamics(self, t, y, mode):
        h = max(0, y[0])
        
        # Logika Aliran Masuk (Inlet)
        q_in = self.config.inlet_flow_rate if mode in ["Isi", "Simultan"] else 0.0
        if h >= self.config.max_height: q_in = min(q_in, self.get_q_out(h))
            
        # Logika Aliran Keluar (Outlet - Torricelli)
        q_out = self.get_q_out(h) if mode in ["Kosongkan", "Simultan"] else 0.0
        
        dh_dt = (q_in - q_out) / self.config.tank_area
        return [dh_dt]

    def get_q_out(self, h):
        if h <= 0: return 0.0
        pipe_area = np.pi * (self.config.outlet_pipe_radius ** 2)
        return self.config.discharge_coeff * pipe_area * np.sqrt(2 * self.g * h)

# ====================
# 3. ANTARMUKA STREAMLIT
# ====================

def main():
    st.set_page_config(page_title="Ops Air Asrama ", layout="wide")

    # --- HEADER & REAL-TIME CLOCK ---
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.title("🚰 Sistem Monitoring & Simulasi Air Asrama")
    with col_t2:
        # Placeholder untuk jam yang terus berjalan
        clock_placeholder = st.empty()

    # --- SIDEBAR PARAMETER ---
    st.sidebar.header("🛠️ Parameter Teknis")
    r = st.sidebar.slider("Radius Silinder Pam (m)", 0.5, 5.0, 1.5)
    h_max = st.sidebar.slider("Tinggi Maksimal Pam (m)", 2.0, 15.0, 5.0)
    q_pump = st.sidebar.slider("Debit Pompa Inlet (m³/s)", 0.01, 0.2, 0.05, format="%.2f")
    r_pipe = st.sidebar.slider("Radius Pipa Distribusi (m)", 0.01, 0.2, 0.05)
    
    st.sidebar.markdown("---")
    sim_duration = st.sidebar.number_input("Durasi Simulasi (menit)", 5, 1440, 60)

    config = WaterTankConfig(
        radius=r, max_height=h_max, 
        inlet_flow_rate=q_pump, 
        outlet_pipe_radius=r_pipe,
        simulation_time=sim_duration
    )

    # --- INSTRUKSI PENGGUNAAN ---
    with st.expander("📖 INSTRUKSI OPERASIONAL (KLIK UNTUK MEMBACA)"):
        st.markdown("""
        ### Cara Menggunakan Simulator:
        1. **Konfigurasi Aset:** Atur dimensi fisik pam (radius & tinggi) di sidebar kiri.
        2. **Pilih Skenario:** * **Isi Saja:** Simulasi pompa menyala tanpa ada penggunaan air di asrama.
           * **Kosongkan Saja:** Simulasi saat listrik mati (pompa mati) namun asrama tetap memakai air.
           * **Simultan:** Simulasi kondisi normal (pompa menyala & air digunakan).
        3. **Analisis Profil:** Perhatikan grafik. Jika garis menyentuh batas merah, pam meluap. Jika menyentuh nol, asrama kehabisan air.
        4. **Optimasi:** Ubah radius pam jika air terlalu cepat habis pada durasi yang Anda inginkan.
        """)

    # --- EKSEKUSI SIMULASI ---
    st.subheader("📊 Hasil Analisis Dinamis")
    mode_input = st.radio("Pilih Skenario Operasional:", 
                          ["Isi", "Kosongkan", "Simultan"], horizontal=True)
    
    model = WaterPhysicsModel(config)
    t_span = (0, config.simulation_time * 60)
    t_eval = np.linspace(0, t_span[1], 1000)
    
    # Kondisi awal: Kosong jika mengisi, Penuh jika mengosongkan
    y0 = [0.0] if mode_input == "Isi" else [config.max_height]
    
    sol = solve_ivp(model.system_dynamics, t_span, y0, t_eval=t_eval, args=(mode_input,))
    
    # Visualisasi
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sol.t/60, y=sol.y[0], name="Level Air (m)", 
                             line=dict(color='#00f2ff', width=3), fill='tozeroy'))
    fig.add_hline(y=config.max_height, line_dash="dash", line_color="red", annotation_text="Batas Meluap")
    
    fig.update_layout(
        template="plotly_dark",
        xaxis_title="Menit ke-",
        yaxis_title="Ketinggian Air (meter)",
        height=450,
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- METRIK UTAMA ---
    m1, m2, m3 = st.columns(3)
    final_h = sol.y[0][-1]
    m1.metric("Ketinggian Akhir", f"{final_h:.2f} m")
    m2.metric("Volume Tersimpan", f"{(config.tank_area * final_h):.2f} m³")
    
    status = "⚠️ KRITIS" if final_h < 0.2 else "✅ AMAN"
    m3.metric("Status Cadangan", status)

    # --- LOGIKA JAM BERJALAN (Loop di akhir agar UI tetap responsif) ---
    while True:
        now = datetime.datetime.now()
        clock_placeholder.markdown(f"""
            <div style="background-color: #1e1e1e; padding: 10px; border-radius: 10px; border: 1px solid #333; text-align: center;">
                <p style="margin: 0; color: #888; font-size: 0.8rem;">WAKTU SISTEM (24H)</p>
                <h2 style="margin: 0; color: #00f2ff; font-family: 'Courier New', Courier, monospace;">
                    {now.strftime('%H:%M:%S')}
                </h2>
            </div>
        """, unsafe_allow_html=True)
        time.sleep(1)

if __name__ == "__main__":
    main()