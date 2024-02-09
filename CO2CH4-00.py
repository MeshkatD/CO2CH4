"""
V.13
Initial Base-Case Model ready for Optimisation analysis
Including the following units:
* DAC - 10,000 t_CO2/y
* Electrolysers
* Fans
* DFM
* TVSA
* Steam Generation
* TVSA Reactor
* TVSA contactors x3
* DFM reactors x2
* DFM heat demand in reaction stage
* Air-Cooler
* Flash Drum Separator
* Integers to Reals
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import math
from IPython.display import display, HTML
from pyomo.environ import *
from pyomo.gdp import *
import locale
import csv  # Import the csv module


# Reactor inlet stream data
# Streams initial flowrate unit is kmole/h
#'CO2':14.25, 'H2':0.0, 'CH4':0.0, 'H2O':0.0, 'N2':28076, 'O2':7535

Streams = {1,
           11, 12, 13, 14, 15, 16,
           2,
           21, 22, 23, 24, 25, 26, 27, 28, 29,
           3,
           4,
           5,
           51,
           52,
           6,
           61, 62, 63, 64, 65, 66,
           635, 636, 665, 666,
           7,
           8,
           9,
           91, 92, 93, 94, 95, 96,
           10,
           20
           }

# mole% of ambient air
Ambient_air = {
    '400-ppm'   :   {'CO2':0.0004, 'H2':0.0, 'CH4':0.0, 'H2O':0.0, 'N2':5910, 'O2':1586},
    }

Initial_Streams = {
    #1   :   {'CO2':2.6, 'H2':0.0, 'CH4':0.0, 'H2O':0.0, 'N2':5122, 'O2':1374},  #1000 tCO2/y
    1   :   {'CO2':26, 'H2':0.0, 'CH4':0.0, 'H2O':0.0, 'N2':51226, 'O2':13747},  #10000 tCO2/y

    }

# MW unit is kg/kmole, ro = kg/m3, cp = kJ/kgmole-C @350 C
Components = {
    'CO2'   :   {'MW':44.01, 'cost':0.0, 'price':0.0, 'ro':1.84, 'cp':47.25},
    'H2'    :   {'MW':2.016, 'cost':0.0, 'price':-200, 'ro':0.0837, 'cp':29.29}, # Hydrogen density @350
    'CH4'   :   {'MW':16.04, 'cost':0.0, 'price':9.0, 'ro':0.657, 'cp':53.78},
    'H2O'   :   {'MW':18.01528, 'cost':0.0, 'price':0.0, 'ro':0.88, 'cp':37.21},  # Water vapor density @ 350  
    'N2'    :   {'MW':28.0134, 'cost':0.0, 'price':0.0, 'ro':1.165, 'cp':0},
    'O2'    :   {'MW':31.999, 'cost':0.0, 'price':0.0, 'ro':1.331, 'cp':0}
    }


Units = {
    1: 'AEL',
    2: 'SOEL',
    3: 'PEMEL',
    4: 'Mixer',
    5: 'DFM Reactor'
    }

# Steam Generation Units
STG_units = {
    1 : 'LP_Steam',
    2 : 'MP_Steam',
    3 : 'HP_Steam'
    }

# H2O --> H2 + 1/2 O2
Stoich_ratio1 = {
    'CO2' : 0,
    'H2' : 1,
    'CH4' : 0,
    'H2O' : -1,
    'N2' : 0,
    'O2' : 0.5
    }

# CO2 + 4H2 --> CH4 + 2H2O
Stoich_ratio2 = {
    'CO2' : -1,
    'H2' : -4,
    'CH4' : 1,
    'H2O' : 2,
    'N2' : 0,
    'O2' : 0
    }

H2_units = {
    1 : 'AEL',
    2 : 'SOEL',
    3 : 'PEMEL'
    }

# Capacity (b) in m3/s Fan maximum head in pa (Seider et al., 2017)
Air_intake_units = {
    'f1' : {'Name' : 'Centrifugal_backward-curved_fan', 'Q_min' : 0.4722 , 'Q_max' : 47.2222, 'Fan_maxH' : 10000},
    'f2' : {'Name' : 'Centrifugal_straight-radial_fan', 'Q_min' : 0.4722 , 'Q_max' : 9.4444, 'Fan_maxH' : 7500},
    'f3' : {'Name' : 'Vane-axial_fan', 'Q_min' : 0.4722 , 'Q_max' : 377.7778, 'Fan_maxH' : 4000},
    }

ADS_units = {
    1 : 'DFM',
    2 : 'TVSA'
    }
# Costing ref.: Towler & Sinnott, 2021 , Ref. for Air-Cooler: Seider et al., 2017
equipment_size_ref = {
    'Compressor_Centrifugal'  : {'S_lower' : 1 ,'S_upper' : 30000 , 'a' : 490000 , 'b' : 16800 , 'n' : 0.6},    # kW
    'Pump'                  : {'S_lower' : 1 ,'S_upper' : 2500 , 'a' : 950 , 'b' : 1770 , 'n' : 0.6},           # kW
    'Axial_Fan'             : {'S_lower' : 100 , 'S_upper' : 170000 , 'a' : 4200 , 'b' : 27 , 'n' : 0.8},       # m3/h
    'Centrifugal_Fan'       : {'S_lower' : 100 , 'S_upper' : 170000 , 'a' : 53000 , 'b' : 28000 , 'n' : 0.8},   # m3/h
    'HEX_Shell&Tube'        : {'S_lower' : 10 , 'S_upper' : 1000 , 'a' : 24000 , 'b' : 46 , 'n' : 1.2},         # m2
    'Furnace_Cylindrical'   : {'S_lower' : 0.2 , 'S_upper' : 60 , 'a' : 68500 , 'b' : 93000 , 'n' : 0.8},       # MW
    'Reactor'               : {'S_lower' : 0.5 , 'S_upper' : 100 , 'a' : 53000 , 'b' : 28000 , 'n' : 0.8},      # m3
    'Air-Cooler'            : {'S_lower' : 40 , 'S_upper' : 150 , 'a' : 0 , 'b' : 2835 , 'n' : 0.45},           # ft2
    'Vertical_Vessel'       : {'S_lower' : 160 , 'S_upper' : 250000 , 'a' : 10000 , 'b' : 29 , 'n' : 0.85}      # kg
    }
# Chemical isotherm parameters for solid sorbents
Sorb_ch = {
    'APDES-NFC'             : {'T0' : 296, 'b0' : 0.560e6, 'Q' : 50000,    't0' : 0.368, 'a' : 0.368, 's0' : 2.310, 'X' : 2.501},
    'Tri-PE-MCM-41'         : {'T0' : 298, 'b0' : 3.135e6, 'Q' : 117.8e3, 't0' : 0.236, 'a' : 0.482, 's0' : 2.897, 'X' : 0.207},
    'MIL-101(Cr)-PEI-800'   : {'T0' : 270, 'b0' : 9.960e6, 'Q' : 68.3e3,  't0' : 0.243, 'a' : 1.802, 's0' : 3.450, 'X' : 4.504},
    'Lewatit-VPOC-106'      : {'T0' : 278, 'b0' : 2.540e6, 'Q' : 91.2e3,  't0' : 0.442, 'a' : 0.520, 's0' : 2.211, 'X' : 0.0}
    }

# Physical isotherm parameters for solid sorbents
Sorb_ph = {
    'APDES-NFC'             : {'T0' : 296,  'b0' : 0,       'Q' : 0,    't0' : 1,       'a' : 0,     's0' : 0,     'X' : 0},
    'Tri-PE-MCM-41'         : {'T0' : 298,  'b0' : 0.636,   'Q' : 2.64e3, 't0' : 0.872,   'a' : 0.003, 's0' : 8.208, 'X' : 4.539},
    'MIL-101(Cr)-PEI-800'   : {'T0' : 270,  'b0' : 93.2,    'Q' : 40.1e3, 't0' : 0.163,   'a' : 2.287, 's0' : 6.205, 'X' : 0.579},
    'Lewatit-VPOC-106'      : {'T0' : 278,  'b0' : 1.51e2,  'Q' : 5.19e3, 't0' : 0.636,   'a' : 2.407, 's0' : 1.840, 'X' : 7.186}
    }

# Thermo-Physical properties for solid sorbents
# dp: particle diameter (mm), ro_s: sorbent density (kg/m3), ro-b: bed density (kg/m3), ro_p: particle density (kg/m3)
# cp: J/Kg/K, Q: J/mol
Sorb_prp = {
    'APDES-NFC'             : {'dp' : 1.3,  'ro_s' : 1589.9, 'ro_p' : 61, 'fb' : 0.908, 'ro_b' : 55.4, 'cp' : 2010},
    'Tri-PE-MCM-41'         : {'dp' : 1.0,  'ro_s' : 2120.0, 'ro_p' : 550, 'fb' : 0.582, 'ro_b' : 320, 'cp' : 1000},
    'MIL-101(Cr)-PEI-800'   : {'dp' : 0.996,  'ro_s' : 1590, 'ro_p' : 500, 'fb' : 0, 'ro_b' : 377.1, 'cp' : 892.5},
    'Lewatit-VPOC-106'      : {'dp' : 0.688,  'ro_s' : 1070, 'ro_p' : 880, 'fb' : 0.773, 'ro_b' : 680, 'cp' : 1580}
    }

def equilibrium_constant(T):
    return 137 * (T**-3.998) * math.exp(158.7/(R*T))

def polytropic_coefficient(k, Ep):
    return 1 / (1-((k-1)/(k*Ep)))

# ******************** Parameter settings *************************
methane_production = 30 # kmol/h

pi = 3.14
M = 1e10                    #BigM
interest_rate = 0.000000012 # interest rate can be deleted in DAC
plant_life = 20             # years
operating_hours = 330*24
CEPCI_2023 = 900
CEPCI_2013 = 567
CEPCI_2007 = 509.7
R = 8.314                   # J/(K·mol)
Z = 0.98                    # compressibility factor
T_amb = 293                 # ambient temperature K
#T_air_In = ((T_amb+5-273)*1.8)+32 # ambient temperature °F
T_air_In = 25               # ambient temperature °C
T_product = 40              # Final product temperature

kWh_cost = 0.22             # [$/kWh] Electricity cost
W_cost = 0.22/3600          # [$/kJ] Electricity cost
Water_cost = 1.1*1.72*1e-3*18.02e-3*1000 # [$/€][€/kg][kg/mol] = [$/kmol] electrolyzer statistisches Bundesamt(link)
p_fuel = 5.6869e-06         # $/kJ -- Towler et. al
n_boiler = 0.8              # Boiler efficiency
n_turb = 0.85               # Steam turbine efficiency, for steam pricing calculations
p_bfw = 0.0                 # $/kmol of boiler feed water

Conv_fac1 = 1.0             # Electrolyzers' conversion
Conv_fac2 = 1.0             # Methanation reactors' conversion
AEL_unit_cost = 463680      # kJ/kmole H2
SOEL_unit_cost = 269900     # kJ/kmole H2
PEMEL_unit_cost = 483840    # kJ/kmole H2
AEL_CAPEX = 950             # $/kW
SOEL_CAPEX = 4200           # $/kW
PEMEL_CAPEX = 1450          # $/kW

AEL_T = 25                  # AEL operating Temperature
SOEL_T = 700                # AEL operating Temperature
PEMEL_T = 25                # AEL operating Temperature

# Plant Steam levels C
T_LP = 150
T_MP = 200
T_HP = 250
#U_Boiler = 88.57 #kJ/h-m2-C for Steam-Flue gas system, based on HYSYS calculations ** SHOULD be updated
#U_Boiler = 118 #kJ/h-m2-C for LP Steam-Flue gas system, based on HYSYS calculations
#U_Boiler = 105.7 #kJ/h-m2-C for MP Steam-Flue gas system, based on HYSYS calculations
U_Boiler = 154 #kJ/h-m2-C update Oct. 2023
DT_min = 20   # min, Temperature difference between Hot & Cold streams in HEX

air_Mu = 1.85e-05 #average dynamic viscosity Pa.s
air_ro = 1.185 #average air density kg/m3
air_MW = 29 #average air molecular weight kg/kmol

#air-intake Fans
DP_max = 10000   #max. output pressure (pa)
nf_fan = 0.6    # nominal fan efficiency
nm_fan = 0.9    # electrical motor efficiency
FM = 2.5        # Fan material factor (equal to Stainless steel)

#DFM Reactor:
#for cell density (CPSI) = 400 monolith :
CPSI = 400
ch_wall = 0.1651/1000 #channel wall thickness (m)
ch_width = 0.001 #chennel width (m)
VR = 7.95e07 #viscous resistance (1/m2)
IR = 7.41  #inertial resistance 1/m
Ri = 0.00105
cpv_monolith = 2.457e3 # kJ/m3.K
cpw_monolith = 0.022e6 # kJ/kmol (Sinha et al 2017)
#Ri = 0.00105
DFM_unit_cost = 272 #$/kg DFM 15% Ni,1% Ru,10% K2O,74% CeO2-Al2O3 (20%-80%)
#DFM_unit_cost = 15 # $/kg (based on Sinha et al., 2017 for MIL-101 price          > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > >
Sorbent_unit_cost = 15 # $/kg (based on Sinha et al., 2017 for MIL-101 price       > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > >
#DFM_SPWeight = 18.511 #kg of DFM on m3 of DFM coat
#DFM_SPWeight = 57.362 #kg of washcoat on m3 of monolith
DFM_SPWeight = 85.43 #kg of washcoat per m3 of monolith (Abdallah et al.,(2023))
#DFM_SPWeight = 210 #kg of washcoat per m3 of monolith (Duyar et al., 2014)
Sorbent_SPWeight = 85.43 #kg of washcoat per m3 of monolith (Abdallah et al.,(2023))
#Sorbent_SPWeight = 210 #kg of washcoat per m3 of monolith (Duyar et al., 2014)
#q_dfm_eq = 0.0014 #Simillar to MIL-101 > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > >
q_dfm_eq = 1.14934e-3 #100% of DFM amb. ads. capacity acc. to to Abdallah et al.,(2023) 1%Ru, 10%Na2O/γ-Al2O3 DFM > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > >
#q_dfm_eq = 6.21e-4 #50% of DFM amb. ads. capacity acc. to to Abdallah et al.,(2023) 1%Ru, 10%Na2O/γ-Al2O3 DFM > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > >
#q_dfm_eq = 4.9e-4 #kmol CO2 adsorbed per kg of DFM
#q_dfm_eq = 2.05e-3 #kmol CO2 adsorbed per kg of DFM Goldman et al., 2023       > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > >
#q_dfm_eq = 2.71e-3 #kmol CO2 adsorbed per kg of DFM - Hypothetical value based on MIL-101 results
k_ads = 0.00023654 # based on curve fitting data on 1%Ru, 10%Na2O/γ-Al2O3 DFM acc. to Abdallah et al.,(2023) > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > >
#k_ads = 0.01 # adsorption rate constant  0.00023654
k_ads_TVSA = 0.0002 # adsorption mass-transfer rate constant for TVSA >> Stampi-Bombelli et al., (2020) > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > >
#k_ads_TVSA = 0.01 # adsorption mass-transfer rate constant for TVSA for confirmation report (min: 0.0035 for base case)
cp_DFM = 0.718 #kJ/kg.K
T_reaction = 523 #Deg C
DH_ads = 151.79 #NiRuNa/CeAl : -151.79 kJ/mol Enthalpy of adsorption
#DH_ads = 121.29 #NiRuK/CeAl: -121.29 kJ/mol Enthalpy of adsorption
#DH_ads = 31.17 #NiRuCa/CeAl: -31.17 kJ/mol Enthalpy of adsorption
H_methanation = 164 #kJ/mol

#TVSA
vf_s = 0.6 #void fraction 1-V_sorbent/V_contactor
Ce_contactor = 25000 # $/m3 contactor (Sabatino et al., 2021) - Assuming 2021 cost basis
Ep = 0.75 # compressors polytropic efficiency
k_is_CO2 = 1.3 # isentropic efficiency for CO2
n_p = polytropic_coefficient(k_is_CO2, Ep)
p_amb = 0.1 # ambient pressure, MPa
p_pbr = 1.0 # operating pressure of the methanation reactor, MPa

#Air-Cooler
#U_Aircooler = 130  #Btu/hr-ft2-F
U_Aircooler = 770   # W/m2-C
L_AC_tube = 40      # Air-Cooler tube length (ft)
AC_tube_gap = 2.5   # Air-Cooler tube spacing (inch)
AC_tube_OD = 1      # OD of the tubes inside AC tube bundle (inch)
AC_Nr = 5           # Number of tube rows in the bundle

#Pressure Vessel
Vessel_thickness = 0.25 # minimum Vessel Thickness for D < 4ft
Shell_density = 0.284 # lb/in3 shell density 
Resid_time = 0.5 # Liquied residence time in vessel (hr)

a_react = equipment_size_ref['Reactor']['a']
b_react = equipment_size_ref['Reactor']['b']
n_react = equipment_size_ref['Reactor']['n']
Sl_react = equipment_size_ref['Reactor']['S_lower']
Su_react = equipment_size_ref['Reactor']['S_upper']

a_contactor = equipment_size_ref['Reactor']['a']
b_contactor = equipment_size_ref['Reactor']['b']
n_contactor = equipment_size_ref['Reactor']['n']
Sl_contactor = equipment_size_ref['Reactor']['S_lower']
Su_contactor = equipment_size_ref['Reactor']['S_upper']

a_Boiler = equipment_size_ref['HEX_Shell&Tube']['a']
b_Boiler = equipment_size_ref['HEX_Shell&Tube']['b']
n_Boiler = equipment_size_ref['HEX_Shell&Tube']['n']
Sl_Boiler = equipment_size_ref['HEX_Shell&Tube']['S_lower']
Su_Boiler = equipment_size_ref['HEX_Shell&Tube']['S_upper']

a_vpump = equipment_size_ref['Compressor_Centrifugal']['a']
b_vpump = equipment_size_ref['Compressor_Centrifugal']['b']
n_vpump = equipment_size_ref['Compressor_Centrifugal']['n']
Sl_vpump = equipment_size_ref['Compressor_Centrifugal']['S_lower']
Su_vpump = equipment_size_ref['Compressor_Centrifugal']['S_upper']

a_compressor = equipment_size_ref['Compressor_Centrifugal']['a']
b_compressor = equipment_size_ref['Compressor_Centrifugal']['b']
n_compressor = equipment_size_ref['Compressor_Centrifugal']['n']
Sl_compressor = equipment_size_ref['Compressor_Centrifugal']['S_lower']
Su_compressor = equipment_size_ref['Compressor_Centrifugal']['S_upper']

a_furnace = equipment_size_ref['Furnace_Cylindrical']['a']
b_furnace = equipment_size_ref['Furnace_Cylindrical']['b']
n_furnace = equipment_size_ref['Furnace_Cylindrical']['n']
Sl_furnace = equipment_size_ref['Furnace_Cylindrical']['S_lower']
Su_furnace = equipment_size_ref['Furnace_Cylindrical']['S_upper']

a_Aircooler = equipment_size_ref['Air-Cooler']['a']
b_Aircooler = equipment_size_ref['Air-Cooler']['b']
n_Aircooler = equipment_size_ref['Air-Cooler']['n']
Sl_Aircooler = equipment_size_ref['Air-Cooler']['S_lower']
Su_Aircooler = equipment_size_ref['Air-Cooler']['S_upper']

a_Vessel = equipment_size_ref['Vertical_Vessel']['a']
b_Vessel = equipment_size_ref['Vertical_Vessel']['b']
n_Vessel = equipment_size_ref['Vertical_Vessel']['n']
Sl_Vessel = equipment_size_ref['Vertical_Vessel']['S_lower']
Su_Vessel = equipment_size_ref['Vertical_Vessel']['S_upper']
 
# ********************* OPTIMISATION MODEL ************************************
m = ConcreteModel()

# Index Sets
m.K = Set(initialize=Streams, ordered=False)
m.C = Set(initialize=Components.keys())
m.A = Set(initialize=Air_intake_units.keys())
m.ADS = Set(initialize=ADS_units.keys())
m.Units = Set(initialize=Units.keys())
m.H2 = Set(initialize=H2_units.keys())
m.SL = Set(initialize=STG_units.keys())
m.SS = Set(initialize=Sorb_ch.keys())

# Decision Variables - Mass & Energy Streams
m.x = Var(m.K, m.C, domain=NonNegativeReals, bounds=(0,1e5))    # kmol/hr

m.y_H2 = Var(m.H2, domain=Boolean)                              # Selection of H2 units
m.y_f = Var(m.A, domain=Boolean)                                # Selection of fans
m.y_fp1 = Var(domain=Boolean)                                   # Conditions for Head factor1
m.y_fp2 = Var(domain=Boolean)                                   # Conditions for Head factor2
m.y_fp3 = Var(domain=Boolean)                                   # Conditions for Head factor3
m.y_fp4 = Var(domain=Boolean)                                   # Conditions for Head factor4
m.y_AD = Var(m.ADS, domain=Boolean)                             # Selection of adsorption units
m.y_stg = Var(m.SL, domain=Boolean)                             # Selection of steam generation level
m.y_sorbent = Var(m.SS, domain=Boolean)                         # Selection of sorbents
m.y_furnace = Var(domain=Boolean)                               # Selection of Furnace
m.y_AC_Z1 = Var(domain=Boolean)                                 # Selection of Air-Cooler FV1
m.y_AC_Z2 = Var(domain=Boolean)                                 # Selection of Air-Cooler FV2
m.y_AC_Z3 = Var(domain=Boolean)                                 # Selection of Air-Cooler FV3
m.y_AC_Z4 = Var(domain=Boolean)                                 # Selection of Air-Cooler FV4
m.y_AC_Z5 = Var(domain=Boolean)                                 # Selection of Air-Cooler FV5


# Decision Variables - Design
m.T = Var(m.K, domain = NonNegativeReals, initialize={7: 350, 8: 170}, bounds=(0,800)) # for stream 8: Set 170 for LP, 220 for MP and 270 for HP
#m.T = Var(m.K, domain = NonNegativeIntegers, bounds=(1,400), initialize={7: 350, 8: 170})
m.T_sat = Param(initialize=150, mutable=False) #Set 150 for LP, 200 for MP and 250 for HP

m.T_des = Var(domain=NonNegativeReals, initialize=120, bounds=(80,120))         # Desorption Temperature C          #||||||||||||||||||||||||||||||||||||

#m.init001 = Constraint(expr= m.T_des == 120)   

m.T_air_Out = Var(domain=NonNegativeReals, initialize=37, bounds=(35,40))      # Air-Cooler Outlet Air Temperature °C                                                                      #||||||||||||||||||||||||||||||||||||
m.T_Hot_In = Var(domain=NonNegativeReals)                                       # Air-Cooler Outlet Air Temperature °C                                                                      #||||||||||||||||||||||||||||||||||||
m.T_Hot_Out = Var(domain=NonNegativeReals)                                      # Air-Cooler Outlet Air Temperature °C
m.LMTD_AC = Var(domain=NonNegativeReals)                                        # LMTD °F

m.p_vac = Var(domain=NonNegativeReals, initialize=0.09, bounds=(0.005,0.09))    # vacuum pressure MPa
#m.init002 = Constraint(expr= m.p_vac == 0.09)                                                                      #||||||||||||||||||||||||||||||||||||
m.DP_fan = Var(m.A, domain=NonNegativeReals)    # Fans produced head (pa)
m.DP = Var(domain=NonNegativeReals)             # reactor pressure drop (pa)
m.DP_cont = Var(domain=NonNegativeReals)        # Contactor pressure drop (pa)
m.DP_AC = Var(domain=NonNegativeReals)          # Air-Cooler air-side pressure drop (inch of water)

m.v = Var(domain=NonNegativeReals, bounds=(0.1,10))    # air average velocity inside monolith channels   
m.v_cont = Var(domain=NonNegativeReals, bounds=(0.1,10))    # air average velocity inside Contactors monolith channels
m.Q_air = Var(domain=NonNegativeReals)
m.Q_air2 = Var(domain=NonNegativeReals)            
m.Q_fan1 = Var(domain=NonNegativeReals)         # fans system 1 capacity
m.Q_fan2 = Var(domain=NonNegativeReals)         # fans system 2 capacity
m.Q_fan3 = Var(domain=NonNegativeReals)         # fans system 3 capacity
m.Q_fan1e = Var(domain=NonNegativeReals)        # fans system 1 each fan capacity
m.Q_fan2e = Var(domain=NonNegativeReals)        # fans system 2 each fan capacity
m.Q_fan3e = Var(domain=NonNegativeReals)        # fans system 3 each fan capacity

m.Q_ex = Var(domain=NonNegativeReals)
m.Q_LP = Var(domain=NonNegativeReals)
m.Q_MP = Var(domain=NonNegativeReals)
m.Q_HP = Var(domain=NonNegativeReals)
m.Q_TVSA = Var(domain=NonNegativeReals)         # kWh external heat required
m.Q_DFM = Var(domain=NonNegativeReals)          # kWh external heat required
m.Q_H2 = Var(domain=NonNegativeReals)           # Heat supplied via Hydrogen stream
m.Q_reaction = Var(domain=NonNegativeReals)     # Heat of reaction
m.Q_Aircooler = Var(domain=NonNegativeReals)    # Heat Duty of Air-Cooler

m.Dq = Var(m.SS)            # kmole of CO2 / kg sorbent
m.q = Var(m.SS)             # mole of CO2 / kg sorbent
m.q_ads = Var(m.SS)         # kmole of CO2 / kg sorbent in T_amb
m.q_des = Var(m.SS)         # kmole of CO2 / kg sorbent in T_des
m.q_dfm = Var(domain=NonNegativeReals, bounds=(0,0.99*q_dfm_eq))                    # kmole of CO2 / kg DFM

m.t_ads = Var(domain=NonNegativeIntegers, initialize=1000, bounds=(1000,1000))      # adsorption time             # ||||||||||||||||||||||||||||||||||||||||||||###
m.t_TVSA = Var(domain=NonNegativeIntegers, initialize=1000, bounds=(1000,1000))     # adsorption time
m.t_ads_TVSA = Var(domain=NonNegativeIntegers, bounds=(1,1000))                     # adsorption time (not in use) x x x x x x x x x x x x x

m.S_react = Var(domain=NonNegativeReals, bounds=(Sl_react,Su_react))                # Size of each reactor (m3)
m.S_contactor = Var(domain=NonNegativeReals, bounds=(Sl_contactor,Su_contactor))                                 # Total Size of contactors (m3)
m.S_Vessel = Var(domain=NonNegativeReals, bounds=(Sl_Vessel,Su_Vessel))             # Total Size of contactors (m3)

#m.S_vpump = Var(domain=NonNegativeReals, bounds=(Sl_vpump,Su_vpump))               # Size of each vpump (kW)
#m.S_compressor = Var(domain=NonNegativeReals, bounds=(Sl_compressor,Su_compressor)) # Size of each compressor (kW)
m.S_vpump = Var(domain=NonNegativeReals)        # Size of each vpump (kW)
m.S_compressor = Var(domain=NonNegativeReals) # Size of each compressor (kW)

m.power_fan1 = Var(domain=NonNegativeReals)                                         # fans system 1 each fan power
m.power_fan2 = Var(domain=NonNegativeReals)                                         # fans system 2 each fan power
m.power_fan3 = Var(domain=NonNegativeReals)                                         # fans system 3 each fan power
m.W_TVSA = Var(domain=NonNegativeReals)                                             # TVSA Total power requirement
m.BHP_Aircooler = Var(domain=NonNegativeReals)                                      # Air-Cooler power requirement (horse power)

m.N_vpump = Var(domain=NonNegativeIntegers, initialize=1, bounds=(1,20))            # Number of vacuum pumps
m.N_compressor = Var(domain=NonNegativeIntegers, initialize=1, bounds=(1,20))       # Number of compressor

m.N_react = Var(domain=NonNegativeIntegers, initialize=28, bounds=(1,50))           # Number of reactors (Min: ) >>>>>>>>>>>>>
m.init003 = Constraint(expr= m.N_react == 16)                                                                           #|||||||||||||||||||||||||||||||||||| ##########
m.N_contactor = Var(domain=NonNegativeIntegers, initialize=20, bounds=(1,30))       # Number of TVSA contactors (Min:14 ) >>>>>>>>>>
m.init004 = Constraint(expr= m.N_contactor == 16)                                                                       #|||||||||||||||||||||||||||||||||||| ##########
m.N_Vessel = Var(domain=NonNegativeIntegers, bounds=(1,5))                          # Number of Vertical Pressure

m.N_Boiler = Var(domain=NonNegativeIntegers, bounds=(1,10))                         # Number of Boilers/HEX
m.N_Aircooler = Var(domain=NonNegativeIntegers, bounds=(1,10))                      # Number of Air-Coolers

m.N_fan1 = Var(domain=NonNegativeIntegers, initialize=20, bounds=(10,100))          # Number of fans in system 1  Min:10
#m.init005 = Constraint(expr= m.N_fan1 == 20)                                                                           #||||||||||||||||||||||||||||||||||||
m.N_fan2 = Var(domain=NonNegativeIntegers, initialize=46, bounds=(1,100))           # Number of fans in system 2
#m.init006 = Constraint(expr= m.N_fan2 == 46)                                                                           #||||||||||||||||||||||||||||||||||||
m.N_fan3 = Var(domain=NonNegativeIntegers, initialize=3, bounds=(1,20))             # Number of fans in system 3
m.init007 = Constraint(expr= m.N_fan3 == 3)                                                                             #||||||||||||||||||||||||||||||||||||
m.N_fan = Var(domain=NonNegativeIntegers, initialize=20, bounds=(1,100))            # Total Number of fans

m.DFM_Weight = Var(domain=NonNegativeReals)                                         # Total Weight of DFM
m.DFM_Volume = Var(domain=NonNegativeReals)                                         # Total Volume of DFM coat on monolith
m.Sorbent_Weight = Var(domain=NonNegativeReals)                                     # Total Weight of sorbents on Contactors 

m.A_ads = Var(domain=NonNegativeReals)                                              # cross-section area of each DFM coat
m.A_Boiler = Var(domain=NonNegativeReals, bounds=(Sl_Boiler,Su_Boiler))             # Size of the Heat Exchanger (m2)
#m.A_Aircooler = Var(domain=NonNegativeReals, bounds=(Sl_Aircooler,Su_Aircooler))   # Required Area of the Air-Cooler (ft2)
m.A_Aircooler = Var(domain=NonNegativeReals)                                        # Required Area of the Air-Cooler (ft2)
m.A_AC_av = Var(domain=NonNegativeReals)                                            # Available heat transfer Area of the Air-Cooler (ft2)
m.D_mon = Var(domain=NonNegativeReals)                                              # Monolith cell diameter
m.D = Var(domain=NonNegativeReals, initialize=4, bounds=(0.5,4))                    # DFM reactor Diameter
m.init008 = Constraint(expr= m.D == 4)                                                                                  #||||||||||||||||||||||||||||||||||||
m.D_cont = Var(domain=NonNegativeReals, initialize=1.5, bounds=(0.5,4))             # Contactor Diameter (Min:2 for N:15)
#m.init009 = Constraint(expr= m.D_cont == 1.5)                                                                          #||||||||||||||||||||||||||||||||||||
m.L = Var(domain=NonNegativeReals, initialize=1, bounds=(1,5))                      # Reactor height/length
#m.init010 = Constraint(expr= m.L == 3)                                                                                 #||||||||||||||||||||||||||||||||||||
m.L_cont = Var(domain=NonNegativeReals, initialize=1, bounds=(1,5))                 # Contactor height/length (Max:8.5 for Fan1)
#m.init011 = Constraint(expr= m.L_cont == 3)                                                                            #||||||||||||||||||||||||||||||||||||

m.D_Vessel = Var(domain=NonNegativeReals)                                           # Vessel Diameter, m
m.L_Vessel = Var(domain=NonNegativeReals)                                           # Vessel Height, m


m.FH1 = Var(domain=NonNegativeReals)
m.FH2 = Var(domain=NonNegativeReals)
m.FH3 = Var(domain=NonNegativeReals)

m.F_A = Var(domain=NonNegativeReals)                                                # Face area of Air-Cooler ft^2
m.F_V = Var(domain=NonNegativeReals, bounds=(400,650))                              # Std. Air Face Velocity ft/min
m.Z_AC = Var(domain=NonNegativeReals)                                               # Dimensionless AC parameter
m.Y_AC = Var(domain=NonNegativeReals)                                               # Air-Cooler Width ft

# Decision Variables - Economy
m.CAPEX = Var(domain=NonNegativeReals)
m.OPEX = Var(domain=NonNegativeReals)

m.Profit = Var(domain=NonNegativeReals)
m.Profit_Product = Var(domain=NonNegativeReals)
m.Profit_Steam = Var(domain=NonNegativeReals)

m.CAPEX_AEL = Var(domain=NonNegativeReals)
m.CAPEX_SOEL = Var(domain=NonNegativeReals)
m.CAPEX_PEMEL = Var(domain=NonNegativeReals)
#m.CAPEX_Reactor = Var(domain=NonNegativeReals)
m.CAPEX_DFM = Var(domain=NonNegativeReals)
m.CAPEX_FAN = Var(domain=NonNegativeReals)
m.CAPEX_Boiler = Var(domain=NonNegativeReals)
m.CAPEX_TVSA = Var(domain=NonNegativeReals)
m.CAPEX_Furnace = Var(domain=NonNegativeReals)
m.CAPEX_Aircooler = Var(domain=NonNegativeReals)
m.CAPEX_Separator = Var(domain=NonNegativeReals)
m.CAPEX_PVessel = Var(domain=NonNegativeReals)

m.OPEX_AEL = Var(domain=NonNegativeReals)
m.OPEX_SOEL = Var(domain=NonNegativeReals)
m.OPEX_PEMEL = Var(domain=NonNegativeReals)
m.OPEX_FAN = Var(domain=NonNegativeReals)
m.OPEX_TVSA = Var(domain=NonNegativeReals)
m.OPEX_DFM = Var(domain=NonNegativeReals)
m.OPEX_Aircooler = Var(domain=NonNegativeReals)

m.Ce_fan1 = Var(domain=NonNegativeReals)                     # purchased equipment cost, 2013 basis
m.Ce_fan2 = Var(domain=NonNegativeReals)                     # purchased equipment cost, 2013 basis
m.Ce_fan3 = Var(domain=NonNegativeReals)                     # purchased equipment cost, 2013 basis
m.Ce_fan1_update = Var(domain=NonNegativeReals)              # purchased equipment cost, 2023 basis
m.Ce_fan2_update = Var(domain=NonNegativeReals)              # purchased equipment cost, 2023 basis
m.Ce_fan3_update = Var(domain=NonNegativeReals)              # purchased equipment cost, 2023 basis
m.Ce_react = Var(domain=NonNegativeReals)                    # purchased Reactor cost, 2007 basis
m.Ce_contactor = Var(domain=NonNegativeReals)                # purchased TVSA contactor cost
m.Ce_Boiler = Var(domain=NonNegativeReals)                   # purchased equipment cost, 2007 basis
m.Ce_vpump = Var(domain=NonNegativeReals)                    # purchased pump (explosion proof motor) cost, 2007 basis
m.Ce_compressor = Var(domain=NonNegativeReals)               # purchased compressor (centrifugal) cost, 2007 basis
m.Ce_PBR = Var(domain=NonNegativeReals)                      # purchased Reactor cost, 2007 basis
m.Ce_Furnace = Var(domain=NonNegativeReals)                  # purchased Furnace cost, 2007 basis
m.Ce_Aircooler = Var(domain=NonNegativeReals)                # purchased Furnace cost, 2013 basis
m.Ce_PVessel = Var(domain=NonNegativeReals)                  # purchased Pressure vessel cost, 2007 basis



m.slack=Var()
m.pslack=Var()
m.nslack=Var()


#annualcapital charge ratio function, inputing i= interest rate and n= plant life
def annualized_capital(i,n):
    ACCR = (i * (1 + i)**n ) / ( (1 + i)**n - 1)
    return ACCR

ACCR = annualized_capital(interest_rate,plant_life)

# ********************* OBJECTIVE FUNCTION ********************************** #
m.TAC = Objective(expr = (m.CAPEX + m.OPEX) - m.Profit, sense = minimize)

# ************************** CONSTRAINTS ************************************ #

# ********************* INITIAL & SEPARATION STATES ************************* #
@m.Constraint(m.C)
def Initial_Condition1(m,c):
    return (m.x[1,c] - Initial_Streams[1][c] == 0)

@m.Constraint(m.C)
def Initial_Condition2(m, c):
    if c == 'H2O':
        return Constraint.Skip   # 'H2' component should be variable
    else:
        return m.x[2, c] == 0.0  # set other components to zero
    
@m.Constraint(m.C)
def DFM_Adsorption1(m,c):
    if c == 'CO2':
        return m.x[62,c] == 0.0
    else:
        return m.x[62,c] == m.x[61,c]

@m.Constraint(m.C)
def DFM_Adsorption2(m,c): 
    if c == 'CO2':
        return m.x[63,c] == m.x[61,c]
    else:
        return m.x[63,c] == 0.0
    
@m.Constraint(m.C)
def VTSA_Adsorption1(m,c):
    if c == 'CO2':
        return m.x[65,c] == 0.0
    else:
        return m.x[65,c] == m.x[64,c]

@m.Constraint(m.C)
def VTSA_Adsorption2(m,c): 
    if c == 'CO2':
        return m.x[66,c] == m.x[64,c]
    else:
        return m.x[66,c] == 0.0

@m.Constraint(m.C)
def Steam_Composition(m, c):
    for i in (91, 92, 93):
        if c != 'H2O':
            return m.x[i,c] == 0.0
        else:
            continue # H2O remains as variable
    return Constraint.Feasible # return a valid expression for other components

@m.Constraint(m.C)
def Flash_Sparator1(m,c): 
    if c == 'H2O':
        return m.x[20,c] == m.x[9,c]
    else:
        return m.x[20,c] == 0.0

@m.Constraint(m.C)
def Flash_Sparator3(m,c): 
    if c == 'H2O':
        return m.x[10,c] == 0.0
    else:
        return m.x[10,c] == m.x[9,c]

# ********************** ENTHALPY CALCULATIONS ****************************** #

# Read the Excel sheet
df = pd.read_excel('C:/Users/md01522/OneDrive - University of Surrey/PhD Surrey/My Project/Python files/project_database.xlsx', sheet_name='Steam_Table')

# Enthalpy finder
def h_fg_calculator(T_sat):
    # Check if the exact value of T_sat exists in the Excel sheet
    if T_sat in df['T_sat'].values:
        h_fg = df.loc[df['T_sat'] == T_sat, 'h_fg'].iloc[0]
    else:
        # If it does not, find the two nearest values of T_sat in the Excel sheet
        lower_T_sat = df.loc[df['T_sat'] <= T_sat, 'T_sat'].max()
        upper_T_sat = df.loc[df['T_sat'] >= T_sat, 'T_sat'].min()
        # Interpolate the corresponding values of h_fg using linear interpolation
        lower_h_fg = df.loc[df['T_sat'] == lower_T_sat, 'h_fg'].iloc[0]
        upper_h_fg = df.loc[df['T_sat'] == upper_T_sat, 'h_fg'].iloc[0]
        h_fg = np.interp(T_sat, [lower_T_sat, upper_T_sat], [lower_DH_vap, upper_DH_vap])
    return h_fg

def h_g_calculator(T_sat):
    # Check if the exact value of T_sat exists in the Excel sheet
    if T_sat in df['T_sat'].values:
        h_g = df.loc[df['T_sat'] == T_sat, 'h_g'].iloc[0]
    else:
        # If it does not, find the two nearest values of T_sat in the Excel sheet
        lower_T_sat = df.loc[df['T_sat'] <= T_sat, 'T_sat'].max()
        upper_T_sat = df.loc[df['T_sat'] >= T_sat, 'T_sat'].min()
        # Interpolate the corresponding values of h_g using linear interpolation
        lower_DH_vap = df.loc[df['T_sat'] == lower_T_sat, 'h_g'].iloc[0]
        upper_DH_vap = df.loc[df['T_sat'] == upper_T_sat, 'h_g'].iloc[0]
        h_g = np.interp(T_sat, [lower_T_sat, upper_T_sat], [lower_DH_vap, upper_DH_vap])
    return h_g

h_fg_LP = h_fg_calculator(T_LP)
h_fg_MP = h_fg_calculator(T_MP)
h_fg_HP = h_fg_calculator(T_HP)

h_g_LP = h_g_calculator(T_LP)
h_g_MP = h_g_calculator(T_MP)
h_g_HP = h_g_calculator(T_HP)

# Price/kg of HP steam
def Steam_Price(p_fuel, p_bfw, h_fg):
    p_hps = ((p_fuel * h_fg)/n_boiler) + p_bfw
    return p_hps

p_hps = Steam_Price(p_fuel, p_bfw, h_fg_HP)
p_mps = p_hps - ((h_g_HP - h_g_MP) * n_turb * W_cost)
p_lps = p_mps - ((h_g_MP - h_g_LP) * n_turb * W_cost) # $/kmol 
   
# ***************************** NODES *************************************** #
# Electrolysers
m.constn01 = Constraint(m.C, rule = lambda m, c : m.x[2,c] == m.x[21,c] + m.x[23,c] + m.x[25,c])
m.constn02 = Constraint(m.C, rule = lambda m, c : m.x[5,c] == m.x[22,c] + m.x[24,c] + m.x[26,c])
m.constn03 = Constraint(m.C, rule = lambda m, c : m.x[21,c] <= M * m.y_H2[1])
m.constn04 = Constraint(m.C, rule = lambda m, c : m.x[23,c] <= M * m.y_H2[2])
m.constn05 = Constraint(m.C, rule = lambda m, c : m.x[25,c] <= M * m.y_H2[3])
m.constn06 = Constraint(expr = m.y_H2[1] + m.y_H2[2] + m.y_H2[3] == 1)
m.constn66666 = Constraint(expr = m.y_H2[2] == 1)           #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

# Furnace
m.constn77777 = Constraint(expr = m.y_furnace == 0)         #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

m.constT01 = Constraint(m.C, rule = lambda m, c : m.T[5] == m.T[22] + m.T[24] + m.T[26])
m.constT02 = Constraint(m.C, rule = lambda m, c : m.T[22] == AEL_T * m.y_H2[1])
m.constT03 = Constraint(m.C, rule = lambda m, c : m.T[24] == SOEL_T * m.y_H2[2])
m.constT04 = Constraint(m.C, rule = lambda m, c : m.T[26] == PEMEL_T * m.y_H2[3])

# Air-Intake
m.constn07 = Constraint(m.C, rule = lambda m, c : m.x[1,c] == m.x[11,c] + m.x[13,c] + m.x[15,c])
m.constn08 = Constraint(m.C, rule = lambda m, c : m.x[11,c] <= M * m.y_f['f1'])
m.constn09 = Constraint(m.C, rule = lambda m, c : m.x[13,c] <= M * m.y_f['f2'])
m.constn10 = Constraint(m.C, rule = lambda m, c : m.x[15,c] <= M * m.y_f['f3'])
m.constn11 = Constraint(expr = m.y_f['f1'] + m.y_f['f2'] + m.y_f['f3'] == 1)
m.constn12 = Constraint(m.C, rule = lambda m, c : m.x[12,c] == m.x[11,c])
m.constn13 = Constraint(m.C, rule = lambda m, c : m.x[14,c] == m.x[13,c])
m.constn14 = Constraint(m.C, rule = lambda m, c : m.x[16,c] == m.x[15,c])
m.constn15 = Constraint(m.C, rule = lambda m, c : m.x[6,c] == m.x[12,c] + m.x[14,c] + m.x[16,c])
m.constn11111 = Constraint(expr = m.y_f['f3'] == 1)          #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

# Adsorption
m.constn16 = Constraint(m.C, rule = lambda m, c : m.x[6,c] == m.x[61,c] + m.x[64,c])
m.constn17 = Constraint(m.C, rule = lambda m, c : m.x[7,c] == m.x[636,c] + m.x[666,c])
m.constn18 = Constraint(m.C, rule = lambda m, c : m.x[61,c] <= M * m.y_AD[1])
m.constn19 = Constraint(m.C, rule = lambda m, c : m.x[64,c] <= M * m.y_AD[2])
m.constn20 = Constraint(expr = m.y_AD[1] + m.y_AD[2] == 1)
m.constn200000 = Constraint(expr = m.y_AD[1] == 1)          #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


# DFM Mixer
m.constn21 = Constraint(m.C, rule = lambda m, c : m.x[635,c] == m.x[63,c] + m.x[51,c])
# TVSA Mixer
m.constn22 = Constraint(m.C, rule = lambda m, c : m.x[665,c] == m.x[66,c] + m.x[52,c])

m.constn23 = Constraint(m.C, rule = lambda m, c : m.x[5,c] == m.x[51,c] + m.x[52,c])
m.constn24 = Constraint(m.C, rule = lambda m, c : m.x[51,c] <= M * m.y_AD[1])
m.constn25 = Constraint(m.C, rule = lambda m, c : m.x[52,c] <= M * m.y_AD[2])

# Steam Generation
m.constn26 = Constraint(expr = m.T[7] == m.T[636] * m.y_AD[1] + m.T[666] * m.y_AD[2])
m.constn27 = Constraint(expr = m.T[636] == 350)     # this constraint shall be changed based on thermo-kinetics of reactor in future
m.constn28 = Constraint(expr = m.T[666] == 350)     # this constraint shall be changed based on thermo-kinetics of reactor in future

m.constn29 = Constraint(m.C, rule = lambda m, c : m.x[7,c] == m.x[8,c])

m.constn30 = Constraint(expr = m.x[91,'H2O'] <= M * m.y_stg[1])
m.constn31 = Constraint(expr = m.x[92,'H2O'] <= M * m.y_stg[2])
m.constn32 = Constraint(expr = m.x[93,'H2O'] <= M * m.y_stg[3])
m.constn33 = Constraint(expr = m.y_stg[1] + m.y_stg[2] + m.y_stg[3] == 1)
#m.constn3333333 = Constraint(expr = m.y_stg[2] == 1)
m.constn34 = Constraint(m.C, rule = lambda m, c : m.x[94,c] == m.x[91,c])
m.constn35 = Constraint(m.C, rule = lambda m, c : m.x[95,c] == m.x[92,c])
m.constn36 = Constraint(m.C, rule = lambda m, c : m.x[96,c] == m.x[93,c])

#Air-Cooler
m.constn40 = Constraint(m.C, rule = lambda m, c : m.x[8,c] == m.x[9,c])

# ***************************** UNIT MODELS ********************************* #

# **************************** Electrolysers ********************************

# AEL electrolyser model & pertaining Costs:

@m.Constraint(m.C)
def AEL(m,c): 
    if c == 'H2':
        return m.x[22,c] - (m.x[21,c] + Stoich_ratio1[c] * Conv_fac1 * m.x[21,'H2O']) == 0
    else:
        return m.x[22,c] == 0.0
@m.Constraint(m.C)
def AEL2(m,c): 
    if c == 'H2':
        return m.x[27,c] == 0
    else:
        return m.x[27,c] - (m.x[21,c] + Stoich_ratio1[c] * Conv_fac1 * m.x[21,'H2O']) == 0

#m.constAEL01 = Constraint(m.C, rule = lambda m, c : m.x[22,c] - (m.x[21,c] + 
                                                              #Stoich_ratio1[c] * Conv_fac1 * m.x[21,'H2O']) == 0)
m.constAEL02 = Constraint(expr = m.OPEX_AEL == (m.x[22,'H2'] * W_cost * AEL_unit_cost + 
                                             m.x[21,'H2O'] * Water_cost) * operating_hours)
m.constAEL03 = Constraint(expr = m.CAPEX_AEL == (m.x[22,'H2'])* AEL_unit_cost*AEL_CAPEX/3600)

# SOEL electrolyser model & pertaining Costs:

@m.Constraint(m.C)
def SOEL(m,c): 
    if c == 'H2':
        return m.x[24,c] - (m.x[23,c] + Stoich_ratio1[c] * Conv_fac1 * m.x[23,'H2O']) == 0
    else:
        return m.x[24,c] == 0.0
@m.Constraint(m.C)
def SOEL2(m,c): 
    if c == 'H2':
        return m.x[29,c] == 0
    else:
        return m.x[29,c] - (m.x[23,c] + Stoich_ratio1[c] * Conv_fac1 * m.x[23,'H2O']) == 0

#m.constSOEL01 = Constraint(m.C, rule = lambda m, c : m.x[24,c] - (m.x[23,c] + 
                                                                #Stoich_ratio1[c] * Conv_fac1 * m.x[23,'H2O']) == 0)
m.constSOEL02 = Constraint(expr = m.OPEX_SOEL == (m.x[24,'H2'] * W_cost * SOEL_unit_cost + 
                                                 m.x[23,'H2O'] * Water_cost)*operating_hours)
m.constSOEL03 = Constraint(expr = m.CAPEX_SOEL == (m.x[24,'H2'])* SOEL_unit_cost * SOEL_CAPEX/3600)

# PEMEL electrolyser model & pertaining Costs:

@m.Constraint(m.C)
def PEMEL(m,c): 
    if c == 'H2':
        return m.x[26,c] - (m.x[25,c] + Stoich_ratio1[c] * Conv_fac1 * m.x[25,'H2O']) == 0
    else:
        return m.x[26,c] == 0.0
@m.Constraint(m.C)
def PEMEL2(m,c): 
    if c == 'H2':
        return m.x[28,c] == 0
    else:
        return m.x[28,c] - (m.x[25,c] + Stoich_ratio1[c] * Conv_fac1 * m.x[25,'H2O']) == 0

#m.constPEMEL01 = Constraint(m.C, rule = lambda m, c : m.x[26,c] - (m.x[25,c] + 
                                                                #Stoich_ratio1[c] * Conv_fac1 * m.x[25,'H2O']) == 0)
m.constPEMEL02 = Constraint(expr = m.OPEX_PEMEL == (m.x[26,'H2'] * W_cost * PEMEL_unit_cost + 
                                                 m.x[25,'H2O'] * Water_cost)*operating_hours)
m.constPEMEL03 = Constraint(expr = m.CAPEX_PEMEL == (m.x[26,'H2'])* PEMEL_unit_cost * PEMEL_CAPEX/3600)

# **************************** Air-intake System ******************************

# Air-intake mass-balance model:
m.constAI01= Constraint(expr = m.Q_fan1 == sum(m.x[11,c]*Components[c]['MW']*
                                               (1/Components[c]['ro'])*(1/3600) for c in m.C)) # m3/s air flow to fans system 1
m.constAI02= Constraint(expr = m.Q_fan2 == sum(m.x[13,c]*Components[c]['MW']*
                                               (1/Components[c]['ro'])*(1/3600) for c in m.C)) # m3/s air flow to fans system 2
m.constAI03= Constraint(expr = m.Q_fan3 == sum(m.x[15,c]*Components[c]['MW']*
                                               (1/Components[c]['ro'])*(1/3600) for c in m.C)) # m3/s air flow to fans system 3

m.constAI04= Constraint(expr = m.Q_fan1e == m.Q_fan1 / m.N_fan1) # m3/s air flow to each fan of system 1
m.constAI05= Constraint(expr = m.Q_fan2e == m.Q_fan2 / m.N_fan2) # m3/s air flow to each fan of system 2
m.constAI06= Constraint(expr = m.Q_fan3e == m.Q_fan3 / m.N_fan3) # m3/s air flow to each fan of system 3

#Fan systems capacity limits
#m.constAI08= Constraint(expr = m.Q_fan1e >= Air_intake_units['f1']['Q_min']) # min Capacity limit for fan of system 1
m.constAI09= Constraint(expr = m.Q_fan1e <= Air_intake_units['f1']['Q_max']) # max Capacity limit for fan of system 1
#m.constAI10= Constraint(expr = m.Q_fan2e >= Air_intake_units['f2']['Q_min']) # min Capacity limit for fan of system 2
m.constAI11= Constraint(expr = m.Q_fan2e <= Air_intake_units['f2']['Q_max']) # max Capacity limit for fan of system 2
#m.constAI12= Constraint(expr = m.Q_fan3e >= Air_intake_units['f3']['Q_min']) # min Capacity limit for fan of system 3
m.constAI13= Constraint(expr = m.Q_fan3e <= Air_intake_units['f3']['Q_max']) # max Capacity limit for fan of system 3

#Fan systems pressure limits
m.constAI14= Constraint(expr = m.DP_fan['f1'] <= Air_intake_units['f1']['Fan_maxH']) # max head limit for system 1 fans
m.constAI15= Constraint(expr = m.DP_fan['f2'] <= Air_intake_units['f2']['Fan_maxH']) # max head limit for system 2 fans
m.constAI16= Constraint(expr = m.DP_fan['f3'] <= Air_intake_units['f3']['Fan_maxH']) # max head limit for system 3 fans
#m.constAI17= Constraint(expr = sum(m.DP_fan[f] * m.y_f[f] for f in m.A) == DP_max)  # it is better to write <=

# Fans' head factor (m.FH1, m.FH2, m.FH3) specification:
m.constAI18= Constraint(expr = m.FH1 == m.y_fp1*1.15 + m.y_fp2*1.3 + m.y_fp3*1.45 + m.y_fp4*1.55)
m.constAI19= Constraint(expr = m.FH2 == m.y_fp1*1.15 + m.y_fp2*1.3 + m.y_fp3*1.45 + m.y_fp4*1.45)
m.constAI20= Constraint(expr = m.FH3 == m.y_fp1*1.15 + m.y_fp2*1.3 + m.y_fp3*1.3 + m.y_fp4*1.3)
m.constAI21= Constraint(expr = m.y_fp1 + m.y_fp2 + m.y_fp3 + m.y_fp4 == 1)
m.constAI22= Constraint(expr = m.DP_fan['f1'] <= m.y_fp1 * 2000 + m.y_fp2 * 3700 + m.y_fp3 * 7500 + m.y_fp4 * DP_max)
m.constAI23= Constraint(expr = m.DP_fan['f2'] <= m.y_fp1 * 2000 + m.y_fp2 * 3700 + m.y_fp3 * 7500 + m.y_fp4 * 7500)
m.constAI24= Constraint(expr = m.DP_fan['f3'] <= m.y_fp1 * 2000 + m.y_fp2 * 4000 + m.y_fp3 * 4000 + m.y_fp4 * 4000)

#Cost function for Centrifugal backward-curved fan (valid from Q = 1,000 to 100,000 ACFM): Seider et al 2016
m.constAI25= Constraint(expr = m.Ce_fan1 == (((1e-6*(m.Q_fan1e*2118.88)**2)+0.264*(m.Q_fan1e*2118.88)+1585)* m.N_fan1 * m.FH1 * FM))
m.constAI26= Constraint(expr = m.Ce_fan1_update == m.Ce_fan1 * (CEPCI_2023/CEPCI_2013))

m.constAI27= Constraint(expr = m.Ce_fan2 == (((3e-6*(m.Q_fan2e*2118.88)**2)+0.264*(m.Q_fan2e*2118.88)+1042.9)* m.N_fan2 * m.FH2 * FM))
m.constAI28= Constraint(expr = m.Ce_fan2_update == m.Ce_fan2 * (CEPCI_2023/CEPCI_2013))

m.constAI29= Constraint(expr = m.Ce_fan3 == (((8e-14*(m.Q_fan3e*2118.88)**3)+(2e-8*(m.Q_fan3e*2118.88)**2)+(0.1562*m.Q_fan3e*2118.88)+1042.9)* m.N_fan3 * m.FH3 * FM))
m.constAI30= Constraint(expr = m.Ce_fan3_update == m.Ce_fan3 * (CEPCI_2023/CEPCI_2013))

# Total fan powers
m.constAI31= Constraint(expr = m.power_fan1 == (m.Q_fan1e * m.DP_fan['f1'] / (1e3*nf_fan*nm_fan )) * m.N_fan1) # m3/s x N/m2 x kJ/1e3J = kJ/s (kW)
m.constAI32= Constraint(expr = m.power_fan2 == (m.Q_fan2e * m.DP_fan['f2'] / (1e3*nf_fan*nm_fan )) * m.N_fan2)
m.constAI33= Constraint(expr = m.power_fan3 == (m.Q_fan3e * m.DP_fan['f3'] / (1e3*nf_fan*nm_fan )) * m.N_fan3)

# AI CAPEX & OPEX
m.constAI34= Constraint(expr= m.CAPEX_FAN == (m.Ce_fan1_update * m.y_f['f1'] + m.Ce_fan2_update * m.y_f['f2'] 
                        + m.Ce_fan3_update*m.y_f['f3']))

m.constAI35= Constraint(expr= m.OPEX_FAN == (m.power_fan1*m.y_f['f1'] + m.power_fan2*m.y_f['f2'] + 
                                             m.power_fan3*m.y_f['f3']) * operating_hours * kWh_cost) #kW * hr * $/kWh = $

m.constAI36= Constraint(expr= m.N_fan == m.N_fan1*m.y_f['f1'] + m.N_fan2*m.y_f['f2'] + m.N_fan3*m.y_f['f3'])


# ********************************* DFM Reactor *******************************
# DFM pressure drop
m.constDFM01 = Constraint(expr = m.Q_air == sum(m.x[6,c]*Components[c]['MW']*(1/Components[c]['ro'])*(1/3600) for c in m.C)) # m3/s air intake
m.constDFM02 = Constraint(expr = m.v == (m.Q_air/m.N_react)/((pi*m.D**2)/4))     # Average air velocity constraint
#m.constDFM03 = Constraint(expr = 1.5 * m.D <= m.L)      # Diameter to height ratio
#m.constDFM04 = Constraint(expr = m.DP == (VR * air_Mu * m.v + (IR * air_ro / 2) * m.v**2) * m.L)  # Monolith Pressure drop constraint
m.constDFM04 = Constraint(expr = m.DP == 8 * m.L * air_Mu * m.v / Ri**2)  # Monolith Pressure drop constraint
#m.constDFM004 = Constraint(expr =  8000 <= m.DP )  # Monolith Pressure drop test
m.constDFM05 = Constraint(expr = m.DP * m.y_AD[1] <= (m.DP_fan['f1']*m.y_f['f1']) + (m.DP_fan['f2']*m.y_f['f2']) + (m.DP_fan['f3']*m.y_f['f3']))

# DFM Reactor stochiometric model
m.constDFM06 = Constraint(m.C, rule = lambda m, c : m.x[636,c] - (m.x[635,c] + Stoich_ratio2[c] * Conv_fac2 * m.x[635,'CO2']) == 0)

# Reactors cost model
m.constDFM07 = Constraint(expr = m.CAPEX_DFM == 2*(m.Ce_react + (DFM_unit_cost * m.DFM_Weight)))
m.constDFM08 = Constraint(expr = m.OPEX_DFM == m.Q_DFM * kWh_cost)
m.constDFM09 = Constraint(expr = m.Ce_react == (a_react + (b_react * (m.S_react ** n_react))) * m.N_react * CEPCI_2023/CEPCI_2007)  # reactor cost equation
m.constDFM10 = Constraint(expr = m.S_react == ((pi * m.D**2) / 4 ) * m.L)       # reactor size equation (based on the monolith chamber only)
#m.constDFM11 = Constraint(expr = m.q_dfm * DFM_SPWeight * m.S_react * 0.95 * m.N_react/m.t_ads == m.x[61,'CO2'])
m.constDFM12 = Constraint(expr = m.x[6,'CO2'] == m.q_dfm * m.DFM_Weight / (m.t_ads/3600))
m.constDFM13 = Constraint(expr = m.S_react * m.N_react * 0.95 * DFM_SPWeight >= m.DFM_Weight)
m.constDFM14 = Constraint(expr = m.q_dfm == q_dfm_eq - q_dfm_eq*exp(-k_ads * m.t_ads))
m.constDFM16 = Constraint(expr = m.Q_DFM == (((m.DFM_Weight*cp_DFM*(T_reaction-T_amb)*0.00028)+ DH_ads*m.x[63,'CO2']/3.6) - m.Q_H2 - m.Q_reaction) * operating_hours) #kWh
m.constDFM17 = Constraint(expr = m.Q_H2 == m.x[5,'H2'] * 577/104) # ~ 577 kW energy for 104 kmol/hr @700C     ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
m.constDFM18 = Constraint(expr = m.Q_reaction == m.x[63,'CO2'] * H_methanation/3.6) # ~ kW energy released in methanation


# ********************************** TVSA *************************************
# TVSA process model
def q_isotherm_ads(qs0, X, B0, Q_ads, T0_ads, t0_ads, a_ads):
    R = 8.314   # J/mol.K
    p = 4e-5    # Co2 partial pressure in amb. condition, MPa (400 ppm in 1 atm)
    T = 293     # amb. temp, K
    #q = m.q     # Adsorption capacity, mol/kg_sorb
    qs = qs0 * exp(X * (1 - T0_ads/T))
    B = B0 * exp(Q_ads/(R*T0_ads) * ((T0_ads/T)-1))
    t = t0_ads + a_ads *(1-(T0_ads/T))
    q = (qs * B * p / (1 + (B*p)**t)**(1/t))
    return q

def q_isotherm_des(qs0, X, B0, Q_ads, T0_ads, t0_ads, a_ads):
    R = 8.314           # J/mol.K
    p = m.p_vac * 4e-4  # Co2 partial pressure in vacuum pressure of p_vac in MPa
    T = m.T_des + 273    # Desorption Temperature, K
    #q = m.q             # Adsorption capacity, mol/kg_sorb
    qs = qs0 * exp(X *(1 - T0_ads/T))
    B = B0 * exp(Q_ads/(R*T0_ads) * ((T0_ads/T)-1))
    t = t0_ads + a_ads*(1-(T0_ads/T))
    q = (qs * B * p / (1 + (B*p)**t)**(1/t))
    return q

m.constTVS01 = Constraint(m.SS, rule = lambda m, s : 0.99* m.Dq[s] >= m.q[s])
m.constTVS02 = Constraint(m.SS, rule = lambda m, s : m.q[s] >= 0)
m.constTVS03 = Constraint(m.SS, rule = lambda m, s : m.q[s] == m.Dq[s] - m.Dq[s]*exp(-k_ads_TVSA * m.t_TVSA))
#m.constTVS04 = Constraint(expr = m.t_TVSA == 3000)
m.constTVS05 = Constraint(expr = m.x[6,'CO2'] == sum(m.q[s] * m.Sorbent_Weight * m.y_sorbent[s] / (m.t_TVSA/3600)  for s in m.SS))
m.constTVS06 = Constraint(expr=sum(m.y_sorbent[s] for s in m.SS) == 1)
m.constTVS000002 = Constraint(expr=m.y_sorbent['MIL-101(Cr)-PEI-800'] == 1)  # 'APDES-NFC', 'Tri-PE-MCM-41', 'MIL-101(Cr)-PEI-800', 'Lewatit-VPOC-106'  >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#m.constTVS002 = Constraint(expr = m.t_ads_TVSA == sum((-1*log(m.Dq[s] - m.q[s])* m.y_sorbent[s])/k_ads_TVSA for s in m.SS))
#m.constTVS003 = Constraint(expr = m.t_ads_TVSA == 100) # simplified approach to prevent long process time
# Sorbent price yet to be added

# Net kmol CO2/kg Sorbents
m.constTVS07 = Constraint(m.SS, rule = lambda m, s : m.Dq[s] == m.q_ads[s] - m.q_des[s])
# kmol CO2/kg of Sorbent Adsorbed
m.constTVS08 = Constraint(m.SS, rule = lambda m, s : m.q_ads[s] * 1e3 == 
                          q_isotherm_ads(Sorb_ch[s]['s0'] , Sorb_ch[s]['X'], Sorb_ch[s]['b0'], Sorb_ch[s]['Q'], Sorb_ch[s]['T0'], Sorb_ch[s]['t0'], Sorb_ch[s]['a'])
                          + q_isotherm_ads(Sorb_ph[s]['s0'] , Sorb_ph[s]['X'], Sorb_ph[s]['b0'], Sorb_ph[s]['Q'], Sorb_ph[s]['T0'], Sorb_ph[s]['t0'], Sorb_ph[s]['a']))
# kmol CO2/kg of Sorbent Desorbed
m.constTVS09 = Constraint(m.SS, rule = lambda m, s : m.q_des[s] * 1e3 == 
                          q_isotherm_des(Sorb_ch[s]['s0'] , Sorb_ch[s]['X'], Sorb_ch[s]['b0'], Sorb_ch[s]['Q'], Sorb_ch[s]['T0'], Sorb_ch[s]['t0'], Sorb_ch[s]['a'])
                          + q_isotherm_des(Sorb_ph[s]['s0'] , Sorb_ph[s]['X'], Sorb_ph[s]['b0'], Sorb_ph[s]['Q'], Sorb_ph[s]['T0'], Sorb_ph[s]['t0'], Sorb_ph[s]['a']))


# TVSA pressure drop
m.constTVS10 = Constraint(expr = m.Q_air2 == sum(m.x[6,c]*Components[c]['MW']*(1/Components[c]['ro'])*(1/3600) for c in m.C)) # m3/s air intake
m.constTVS11 = Constraint(expr = m.v_cont == (m.Q_air2/m.N_contactor)/((pi*m.D_cont**2)/4))     # Average air velocity constraint
#m.constTVS19 = Constraint(expr = 1.5 * m.D_cont <= m.L_cont)      # Diameter to height ratio
#m.constTVS20 = Constraint(expr = m.DP_cont == (VR * air_Mu * m.v_cont + (IR * air_ro / 2) * m.v_cont**2) * m.L)  # Monolith Pressure drop constraint
m.constTVS12 = Constraint(expr = m.DP_cont == 8 * m.L_cont * air_Mu * m.v_cont / Ri**2)  # Monolith Pressure drop constraint
#m.constTVS22 = Constraint(expr = m.DP_cont == 7500 )  # Monolith Pressure drop constraint
m.constTVS13 = Constraint(expr = m.DP_cont * m.y_AD[2] <= (m.DP_fan['f1']*m.y_f['f1']) + (m.DP_fan['f2']*m.y_f['f2']) + (m.DP_fan['f3']*m.y_f['f3']))

m.constTVS14 = Constraint(expr = m.S_contactor == ((pi * m.D_cont**2) / 4 ) * m.L_cont)       # Contactor size equation (based on the monolith chamber only)


# TVSA sizings & costs
m.constTVS15 = Constraint(expr = m.CAPEX_TVSA == (m.Ce_contactor*3) + m.Ce_vpump + m.Ce_compressor + m.Ce_PBR + (Sorbent_unit_cost * m.Sorbent_Weight *3))
m.constTVS16 = Constraint(expr = m.OPEX_TVSA == (m.Q_TVSA + m.W_TVSA) * kWh_cost)
m.constTVS17 = Constraint(expr = m.W_TVSA == (m.S_compressor * m.N_compressor + m.S_vpump * m.N_vpump) * operating_hours)
m.constTVS18 = Constraint(expr = m.Q_TVSA == ((sum(Sorb_prp[s]['cp'] * ((m.T_des + 273) - T_amb) * m.Sorbent_Weight * m.y_sorbent[s]*0.00028/1000 for s in m.SS))+
                          (sum(Sorb_ch[s]['Q'] * m.x[66,'CO2'] * m.y_sorbent[s]/(3600) for s in m.SS))) * operating_hours) #kWh
#m.constTVS09 = Constraint(expr = m.Q_TVSA == ((cpv_monolith * ((m.T_des + 273) - T_amb) * m.S_contactor * m.N_contactor)/m.t_TVSA) * operating_hours)
#m.constTVS09 = Constraint(expr = m.Q_TVSA == (cpw_monolith * m.x[66,'CO2']/3600) * operating_hours)
m.constTVS19 = Constraint(expr = m.Ce_contactor == (a_contactor + (b_contactor * (m.S_contactor ** n_contactor))) * m.N_contactor * CEPCI_2023/CEPCI_2007)
m.constTVS20 = Constraint(expr = m.Ce_vpump == (a_vpump + (b_vpump * (m.S_vpump ** n_vpump))) * m.N_vpump * CEPCI_2023/CEPCI_2007)
m.constTVS21 = Constraint(expr = m.Ce_compressor == (a_compressor + (b_compressor * (m.S_compressor ** n_compressor))) * m.N_compressor * CEPCI_2023/CEPCI_2007)
m.constTVS22 = Constraint(expr = m.S_contactor * m.N_contactor * 0.95 * Sorbent_SPWeight >= m.Sorbent_Weight)
m.constTVS23 = Constraint(expr = m.S_vpump == (1/Ep) * Z * R * (m.T_des + 273) * n_p/(n_p - 1) * ((p_amb/m.p_vac)**((n_p - 1)/n_p) - 1) *m.x[66,'CO2']/(3600 * m.N_vpump)) # kW of a vacuum pump
m.constTVS24 = Constraint(expr = m.S_compressor == (1/Ep) * Z * R * T_amb * n_p/(n_p - 1) * ((p_pbr/p_amb)**((n_p - 1)/n_p) - 1) * m.x[66,'CO2']/(3600 * m.N_compressor)) # kW of a compressor
m.constTVS25 = Constraint(expr = m.Ce_PBR == (a_react + (b_react * (0.5 ** n_react))) * CEPCI_2023/CEPCI_2007)  # PB reactor cost (assuming the min. size, 0.5 m3)

# PB Reactor stochiometric model
m.constPBR01 = Constraint(m.C, rule = lambda m, c : m.x[666,c] - (m.x[665,c] + Stoich_ratio2[c] * Conv_fac2 * m.x[665,'CO2']) == 0)

# ***************************** Steam Generation ******************************
m.constSTG01= Constraint(expr = m.T_sat == T_LP * m.y_stg[1] + T_MP * m.y_stg[2] + T_HP * m.y_stg[3])
m.constSTG02= Constraint(expr = m.T[8] >= DT_min + m.T_sat)
m.constSTG04= Constraint(expr = m.Q_ex == sum(m.x[7,c] * Components[c]['cp'] for c in m.C)*(m.T[7] - m.T[8]))
m.constSTG05= Constraint(expr = m.Q_ex == m.Q_LP + m.Q_MP + m.Q_HP)
m.constSTG06= Constraint(expr = m.Q_LP <= M * m.y_stg[1])
m.constSTG07= Constraint(expr = m.Q_MP <= M * m.y_stg[2])
m.constSTG08= Constraint(expr = m.Q_HP <= M * m.y_stg[3])
m.constSTG09= Constraint(expr = m.x[91,'H2O'] == m.Q_LP / h_fg_LP)
m.constSTG10= Constraint(expr = m.x[92,'H2O']  == m.Q_MP / h_fg_MP)
m.constSTG11= Constraint(expr = m.x[93,'H2O']  == m.Q_HP / h_fg_HP)

# CAPEX for boiler
m.constHX02 = Constraint(expr = m.CAPEX_Boiler - (m.Ce_Boiler * (CEPCI_2023/CEPCI_2007)) == 0)
# Cost function for Boiler
m.constHX03 = Constraint(expr = m.Ce_Boiler == (a_Boiler + (b_Boiler * 
                                                            (m.A_Boiler ** n_Boiler)))*m.N_Boiler)  #Boiler cost equation, 2007 basis (to be checked)

# HEX Area
log_term = log(m.T[7] - m.T_sat) - log(m.T[8] - m.T_sat) + 1e-9
m.constHX04 = Constraint(expr = m.A_Boiler == m.Q_ex / (U_Boiler * ((m.T[7].value - m.T[8].value) / log_term)))

# Furnace
m.constFRN01 = Constraint(expr = m.CAPEX_Furnace - (m.Ce_Furnace * (CEPCI_2023/CEPCI_2007)) == 0)
# Cost function for Boiler
m.constFRN02 = Constraint(expr = m.Ce_Furnace == (a_furnace + (b_furnace * 
                                                            (0.54 ** n_furnace))))

# ******************************* Air-Cooler **********************************
# CAPEX for Air-Cooler
m.constAC01 = Constraint(expr = m.CAPEX_Aircooler - (m.Ce_Aircooler * (CEPCI_2023/CEPCI_2013)) == 0)
# Cost function for Air-Cooler
m.constAC02 = Constraint(expr = m.Ce_Aircooler == (a_Aircooler + (b_Aircooler * 
                                                            (m.A_Aircooler ** n_Aircooler))))  # AC cost equation, 2013 basis
# OPEX for Air-Cooler
m.constAC03 = Constraint(expr = m.OPEX_Aircooler == (m.BHP_Aircooler/1.341)*operating_hours*kWh_cost)

# Air-Cooler Area
#m.constAC04 = Constraint(expr = m.T_air_Out == 36.7) #in C
m.constAC06 = Constraint(expr = m.LMTD_AC == ((m.T[8] - m.T_air_Out)-(T_product - T_air_In)) /(log((m.T[8] - m.T_air_Out)/(T_product - T_air_In)) + 1e-9)) # LMTD in C
m.constAC07 = Constraint(expr = m.A_Aircooler == (m.Q_Aircooler / ((U_Aircooler* 3.6 * m.LMTD_AC)+1e-9))*10.764)  # Area in ft2
m.constAC08 = Constraint(m.C, rule = lambda m, c : m.Q_Aircooler == sum(m.x[8,c]*Components[c]['cp'] for c in m.C)*(m.T[8]-T_product) + m.x[8,'H2O']*h_fg_calculator(100)) # Duty in kJ/hr
m.constAC09 = Constraint(expr = m.Z_AC == (m.T[8]-T_product)/(m.T[8]-T_air_In))
m.constAC10 = Constraint(expr = 0.4*m.y_AC_Z1 + 0.5*m.y_AC_Z2 + 0.7*m.y_AC_Z3 + 0.8*m.y_AC_Z4 + m.y_AC_Z5 - (m.Z_AC*100/(U_Aircooler/5.678)) <= 0.09)
m.constAC11 = Constraint(expr = 0.4*m.y_AC_Z1 + 0.5*m.y_AC_Z2 + 0.7*m.y_AC_Z3 + 0.8*m.y_AC_Z4 + m.y_AC_Z5 - (m.Z_AC*100/(U_Aircooler/5.678)) >= 0)
m.constAC12 = Constraint(expr = m.y_AC_Z1 + m.y_AC_Z2 + m.y_AC_Z3 + m.y_AC_Z4 + m.y_AC_Z5 == 1)
m.constAC13 = Constraint(expr = m.F_V == 650*m.y_AC_Z1 + 600*m.y_AC_Z2 + 550*m.y_AC_Z3 + 450*m.y_AC_Z4 + 400*m.y_AC_Z5)  # F_V in ft/min
m.constAC14 = Constraint(expr = m.F_A == (m.Q_Aircooler/1.055)/((m.F_V *((m.T_air_Out*1.8+32)-(T_air_In*1.8+32))*1.95)+ 1e-9)) # F_A in ft2, Q in BTU/hr, Temp in F
m.constAC15 = Constraint(expr = m.Y_AC == m.F_A/L_AC_tube) # Bundle width (ft)
m.constAC16 = Constraint(expr = (m.T_air_Out*1.8+32) == (T_air_In*1.8+32) + ((m.Q_Aircooler/1.055)/((m.Y_AC*m.F_V*L_AC_tube*1.95)+ 1e-9)))
m.constAC17 = Constraint(expr = m.A_AC_av == AC_Nr * (m.Y_AC/(AC_tube_gap/12))*3.14*(AC_tube_OD/12)*L_AC_tube) # Available heat transfer area (ft2)
# Air-Cooler break horse power
m.constAC18 = Constraint(expr = m.BHP_Aircooler == (m.F_V*m.F_A*(m.T_air_Out + 273)*(m.DP_AC+0.1))/1.15e6)
m.constAC19 = Constraint(expr = m.DP_AC == 0.0037*AC_Nr*(m.F_V/100)**1.8)

# *********************** Separator (Pressure-Vessel) *************************
# CAPEX for Vertical Pressure Vessel
m.constPV01 = Constraint(expr = m.CAPEX_PVessel - (m.Ce_PVessel * (CEPCI_2023/CEPCI_2007)) == 0)
m.constPV02 = Constraint(expr = m.Ce_PVessel == (a_Vessel + (b_Vessel * 
                                                            (m.S_Vessel ** n_Vessel))))  # pressure vessel cost equation, 2007 basis
m.constPV03 = Constraint(expr = m.S_Vessel == 3.14*((m.D_Vessel*39.37) + Vessel_thickness)*((m.L_Vessel*39.37) + (0.8*m.D_Vessel*39.37))*Vessel_thickness*Shell_density/2.205) # kg Vessel
m.constPV04 = Constraint(expr = m.D_Vessel == (2*m.x[9,'H2O']*18*Resid_time/(1000*3.14))**(1/3))
m.constPV05 = Constraint(expr = m.L_Vessel == 4 * m.D_Vessel)


# ***************************** COST FUNCTIONS ********************************
# Annual Profit equation:
m.constpr01 = Constraint(expr = m.Profit - m.Profit_Product  - m.Profit_Steam == 0)
m.constpr02 = Constraint(expr = m.Profit_Product - (sum((m.x[7,c])*Components[c]['price'] for c in m.C))*operating_hours == 0)
m.constpr03 = Constraint(expr = m.Profit_Steam - ((m.x[91,'H2O'] * p_lps) + 
                                                (m.x[92,'H2O'] * p_mps) + (m.x[93,'H2O'] * p_hps)) * operating_hours == 0)

# Annualized CAPEX equation:
m.constCX = Constraint(expr = m.CAPEX - (m.CAPEX_FAN + m.CAPEX_DFM * m.y_AD[1] + m.CAPEX_TVSA * m.y_AD[2] + 
                                         m.CAPEX_AEL+m.CAPEX_SOEL+m.CAPEX_PEMEL+m.CAPEX_Boiler + m.CAPEX_Furnace*m.y_furnace
                                         + m.CAPEX_Aircooler + m.CAPEX_Separator + m.CAPEX_PVessel) * ACCR == 0)
#m.constCX_ads = Constraint(expr = m.CAPEX_ads - (m.CAPEX_DFM * m.y_AD[1] + m.CAPEX_TVSA * m.y_AD[2]) == 0)
m.constOX = Constraint(expr = m.OPEX - m.OPEX_FAN - (m.OPEX_TVSA*m.y_AD[2]) - (m.OPEX_DFM*m.y_AD[1]) 
                       - (m.OPEX_AEL+m.OPEX_SOEL+m.OPEX_PEMEL) - m.OPEX_Aircooler == 0)

# Plant production rate
#m.constpr04 = Constraint(expr = m.x[636,'CH4'] == methane_production)

# solve
solver=SolverFactory('gams')
#io_options=dict(MaxTime=100)
#results = solver.solve(m, tee=True, solver='baron', io_options=io_options)
results = solver.solve(m, tee=True, solver='baron')
#m.pprint()
###############################################################################

# set the locale to use commas as thousands separators
locale.setlocale(locale.LC_ALL, '')
# get the cost values and format it with commas

def format_number(value):
    # format the value using the current locale
    return locale.format_string("%.0f", value, grouping=True)

# create a dictionary of the variable values
x_dict = {}
for k in m.K:
    for c in m.C:
        value = m.x[k, c].value
        if value is not None:
            x_dict[f'x_{k}_{c}'] = np.round(value, 4)

x_df = pd.DataFrame.from_dict(x_dict, orient='index', columns=['Value'])
x_df.index = pd.MultiIndex.from_tuples([tuple(col.split('_')[1:]) for col in x_df.index], names=['K', 'C'])
x_df = x_df.unstack().droplevel(level=0, axis=1)

# print the dataframe
print("")
print(x_df)
print("")

# print the formatted TAC value
print(50*"*")
print("* Total Annaul Cost: ", format_number(m.TAC()), "USD")
print("* Revenue: ", format_number(m.Profit()), "USD *")
print("* Annual Operational Cost of the Plant (OPEX): ", format_number(m.OPEX()), "USD")
print("* Annualized Capital Cost of the Plant (CAPEX): ", format_number(m.CAPEX()), "USD")
print("")
print(50*"*")

print("")
print(" ****** Air-intake System ****** ")
print("")
for f in m.A:
    if m.y_f[f]() == 1:
        print("* Number of Fans: ", m.N_fan())
        print("* Selected Teachnology: ", Air_intake_units[f]['Name'])
print("* Air capturing rate: ", round(m.Q_air(),2), "m3/s")

print("* Ce_fan1_update: ", format_number(m.Ce_fan1_update()))
print("* Ce_fan2_update: ", format_number(m.Ce_fan2_update()))
print("* Ce_fan3_update: ", format_number(m.Ce_fan3_update()))
print("* OPEX_FAN: ", format_number(m.OPEX_FAN()))
print("* CAPEX_FAN: ", format_number(m.CAPEX_FAN()))
print("* FH1: ", m.FH1())
print("* FH2: ", m.FH2())
print("* FH3: ", m.FH3())
print("* power_fan1: ", format_number(m.power_fan1()))
print("* power_fan2: ", format_number(m.power_fan2()))
print("* power_fan3: ", format_number(m.power_fan3()))
print("* Q_fan1e: ", format_number(m.Q_fan1e()))
print("* Q_fan2e: ", format_number(m.Q_fan2e()))
print("* Q_fan3e: ", format_number(m.Q_fan3e()))
print("* Q_air: ", format_number(m.Q_air()))
for f in m.A:
    print("* DP_fan for ",Air_intake_units[f]['Name'],":", format_number(m.DP_fan[f]()))
print(50*".")
print("")

print(" ****** Hydrogen production ****** ")
print("")
for i in m.H2:
    if m.y_H2[i]() == 1:
        print("* Selected Technology: ", H2_units[i])
print("* H2 Production OPEX : ", format_number(m.OPEX_AEL() + m.OPEX_SOEL() + m.OPEX_PEMEL()), "USD")
print("* H2 Production CAPEX : ", format_number(m.CAPEX_AEL() + m.CAPEX_SOEL() + m.CAPEX_PEMEL()), "USD")
print(50*".")

print("")
print(" ****** Adsorption & Reaction ****** ")
print("")

for i in m.ADS:
    if m.y_AD[i]() == 1:
        print("* Selected Adsorption unit: ", ADS_units[i])
print("")
print("* DFM Total Capital Cost (CAPEX_DFM): ", format_number(m.CAPEX_DFM()), "USD")
print("* DFM Total Operating Cost (OPEX_DFM): ", format_number(m.OPEX_DFM()), "USD")
print("* DFM External Heat requirement (Q_DFM): ", format_number(m.Q_DFM()), "kWh")
print("* Air Linear velocity inside DFM reactor (v): ", round(m.v(),2), "m/s")
print("* DFM Reactors Pressure drop (DP): ", round(m.DP(),2), "Pa")
print("* Number of Reactors in each train (N_react): ", round(m.N_react()))
print("* Number of Reactors in 2 trains (2xN_react): ", round(2*m.N_react()))
print("* Each DFM Reactors Size (S_react): ", round(m.S_react(),2), "m3")
print("* Each DFM Reactors Diameter (D): ", round(m.D(),2), "m")
print("* Each DFM Reactors Height (L): ", round(m.L(),2), "m")
print("* Total DFM Weight in each train (DFM_Weight): ", format_number(m.DFM_Weight()), "kg")
print("* Total DFM Cost in each trains: ", format_number(DFM_unit_cost*m.DFM_Weight()), "USD")
print("* Total DFM Weight in 2 trains (2xDFM_Weight): ", format_number(2*m.DFM_Weight()), "kg")
print("* Total DFM Cost in 2 trains: ", format_number(2*DFM_unit_cost*m.DFM_Weight()), "USD")
print("* Ann. DFM Cost in 2 trains: ", format_number(2*DFM_unit_cost*m.DFM_Weight()*ACCR), "USD")
print("* m.t_ads: ", m.t_ads(), "s")
print("* k_ads: ", k_ads, "1/s")
print("* q_dfm_eq: ", q_dfm_eq, "kmol CO2/kg_sorb")
print("* q_dfm: ", m.q_dfm(), "kmol CO2/kg_sorb")
print("* Channels IR", Ri, 'm')
print("")

print("* TVSA Total Capital cost (CAPEX_TVSA): ", format_number(m.CAPEX_TVSA()), "USD")
print("* TVSA Total Operating Cost (OPEX_TVSA): ", format_number(m.OPEX_TVSA()), "USD")
print("* TVSA Comp./Vpump elect. consumption (W_TVSA): ", format_number(m.W_TVSA()), "kWh")
print("* TVSA Heat required (Q_TVSA): ", format_number(m.Q_TVSA()), "kWh")
print("* Air Linear velocity inside contactors (v_cont): ", round(m.v_cont(),2), "m/s")
print("* Contactor's pressure drop (DP_cont): ", round(m.DP_cont(),2), "Pa")
print("* Number of contactors in each train (N_contactor): ", round(m.N_contactor()))
print("* Number of contactors in 3 train (3xN_contactor): ", round(3*m.N_contactor()))
print("* Size of each contactor (S_contactor): ", round(m.S_contactor(),2), "m3")
print("* Contactor Diameter (D_cont): ", round(m.D_cont(),2), "m")
print("* Contactor Height (L_cont): ", round(m.L_cont(),2), "m")
print("* Total Sorbent weight in each train (Sorbent_Weight): ", format_number(m.Sorbent_Weight()), "kg")
print("* Total Sorbent weight in 3 trains (3xSorbent_Weight): ", format_number(3*m.Sorbent_Weight()), "kg")
print("* Vacuum Pump Size (S_vpump): ", round(m.S_vpump(),2), "kW")
print("* Number of Vacuum Pumps (N_vpump): ", round(m.N_vpump()))
print("* Vacuum Pump Cost (Ce_vpump): ", format_number(m.Ce_vpump()), "USD")
print("* Compressor Size (S_compressor): ", round(m.S_compressor(),2), "kW")
print("* Number of Compressors (N_compressor): ", round(m.N_compressor()))
print("* Compressor Cost (Ce_compressor): ", format_number(m.Ce_compressor()), "USD")
print("* Desorption Temperature (T_des): ", format_number(m.T_des()), "C")
print("* Vacuum Pressure (p_vac): ", round(m.p_vac(),3), "MPa")
print("* PBR capital cost (Ce_PBR): ", format_number(m.Ce_PBR()), "$")
print("* m.t_TVSA: ", m.t_TVSA(), "s")
print("* k_ads_TVSA: ", k_ads_TVSA, "1/s")
print("* Channels IR", Ri, 'm')
print("* TVSA Sorbent options: ")

for s in m.SS:
    print("      ", s)
print("* Calculated equilibrium capacity sorbents (Dq):")
for s in m.SS:
    print("      ", s," :", round(m.Dq[s](),6), "kmol CO2/kg Sorbent")
for s in m.SS:
    if m.y_sorbent[s]()==1:
        print("* The selected Sorbent: ", s)
print("* calculated sorption capacity (q):")
for s in m.SS:
    print("      ", s," :", round(m.q[s](),6), "kmol CO2/kg Sorbent")
print("* calculated capacity in desorption condition (q_des):")
for s in m.SS:
    print("      ", s," :", round(m.q_des[s](),6), "kmol CO2/kg Sorbent")
print(50*".")
print("")
print(" ****** Steam Generation ****** ")
print("")
for i in m.SL:
    if m.y_stg[i]() == 1:
        print("* Selected steam level: ", STG_units[i])

print("* The Temperatures levels: ")
print("* Boiler flue gas Temperature (T7): ", round(m.T[7](),1), " C")
print("* Flue gas Exit Temperature (T8): ", round(m.T[8](),1), " C")
print("* Steam Temperature (T_sat): ", round(m.T_sat(),1), " C")
print("* Heat duty of the Biler: ", format_number(m.Q_ex()), "kJ")
print("* LMTD for boiler: ", round(((m.T[7]() - m.T[8]()) / log_term()),1))
print("* Heat transfer Area of Boiler: ", format_number(m.A_Boiler()), "m2")
print("* Steam revenue: ", format_number(m.Profit_Steam()), "USD")
print("* Steam Generation CAPEX: ", format_number(m.CAPEX_Boiler()), "USD")
print("* Steam Generation Annualized CAPEX: ", format_number(m.CAPEX_Boiler()* ACCR), "USD")

print(50*".")
print("")
print(" ****** Air-Cooler ****** ")
print("")
print("CAPEX_Aircooler: ", format_number(m.CAPEX_Aircooler()),"USD")
print("OPEX_Aircooler: ", format_number(m.OPEX_Aircooler()),"USD")
print("BHP_Aircooler: ", format_number(m.BHP_Aircooler()),"bhp")
print("Q_Aircooler: ", format_number(m.Q_Aircooler()),"kJ/hr")
print("LMTD_AC: ", format_number(m.LMTD_AC()),"°C")
print("A_req:", format_number(m.A_Aircooler()),"ft2")
print('m.A_AC_av :', format_number(m.A_AC_av()),"ft2")
print('h_fg', format_number(h_fg_calculator(100)), "kJ/kmol")
print('m.Z_AC', round(m.Z_AC(),2))
print('F_V:', round(m.F_V()), "ft/min")
print('m.Z_AC*100/(U_Aircooler/5.678)', round(m.Z_AC()*100/(U_Aircooler/5.678),2))
print('T_air_Out: ', format_number(m.T_air_Out()),"°C")
print(50*".")

print("")
print(" ****** Water Separator ****** ")
print("")
print("CAPEX_PVessel: ", format_number(m.CAPEX_PVessel()),"USD")
print("Ce_PVessel: ", format_number(m.Ce_PVessel()),"USD")
print("S_Vessel: ", format_number(m.S_Vessel()),"kg")
print("D_Vessel: ", round(m.D_Vessel(),2),"m")
print("L_Vessel: ", round(m.L_Vessel(),2),"m")

print(50*".")

print("* Furnace Cost: ", format_number(m.CAPEX_Furnace()), "USD")

print(50*"*")
# Creating a list to store the data for each run
data_list = []

sens_data = {
    'TAC': m.TAC(),
    'CAPEX': m.CAPEX(),
    'OPEX': m.OPEX(),
    'Revenue': m.Profit(),
    'CAPEX_FAN': m.CAPEX_FAN(),
    'OPEX_FAN': m.OPEX_FAN(),
    'N_fan': m.N_fan(),
    'Fan_Power': m.power_fan1()*m.y_f['f1']() + m.power_fan2()*m.y_f['f2']()+m.power_fan3()*m.y_f['f3'](),
    'CAPEX_H2': m.CAPEX_AEL()+m.CAPEX_SOEL()+m.CAPEX_PEMEL(),
    'OPEX_H2': m.OPEX_AEL()+m.OPEX_SOEL()+m.OPEX_PEMEL(),
    'CAPEX_TVSA': m.CAPEX_TVSA(),
    'OPEX_TVSA': m.OPEX_TVSA(),
    'N_contactor': m.N_contactor(),
    'S_contactor': m.S_contactor(),
    'v_cont': m.v_cont(),
    'D_cont': m.D_cont(),
    'L_cont': m.L_cont(),
    'DP_cont': m.DP_cont(),
    'Sorbent_Weight': m.Sorbent_Weight(),
    'k_ads_TVSA': k_ads_TVSA,
    'Ri': Ri,
    'T_des': m.T_des(),
    'p_vac': m.p_vac(),
    'q': m.q['APDES-NFC'](),
    'CAPEX_Boiler': m.CAPEX_Boiler(),
    'A_Boiler': m.A_Boiler(),
    'Revenue_Steam': m.Profit_Steam(),
    }
data_list.append(sens_data)
# Define the CSV file name
csv_file = 'sensitivity_output.csv'

# Write the data to a CSV file
with open(csv_file, mode='w', newline='') as file:
    fieldnames = ['TAC', 'CAPEX', 'OPEX', 'Revenue', 
                  'CAPEX_FAN', 'OPEX_FAN', 'N_fan', 'Fan_Power',
                  'CAPEX_H2', 'OPEX_H2',
                  'CAPEX_TVSA', 'OPEX_TVSA', 'N_contactor', 'S_contactor', 'v_cont', 'D_cont', 'L_cont', 'DP_cont', 'Sorbent_Weight', 'k_ads_TVSA', 'Ri', 'T_des', 'p_vac', 'q',
                  'CAPEX_Boiler', 'A_Boiler', 'Revenue_Steam'
                  ]
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data_list)


# Print a message to indicate that the data has been written to the CSV file
print(f"Data has been written to '{csv_file}'.")

data_list2 = []

sens_data2 = {
    'TAC': m.TAC(),
    'CAPEX': m.CAPEX(),
    'CAPEX_TVSA': m.CAPEX_TVSA(),
    }
data_list2.append(sens_data2)
# Define the CSV file name
csv_file2 = 'sensitivity_output2.csv'

# Write the data to a CSV file
with open(csv_file2, mode='w', newline='') as file:
    fieldnames = ['TAC', 'CAPEX',
                  'CAPEX_TVSA' 
                  ]
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data_list2)

# Print a message to indicate that the data has been written to the CSV file
print(f"Data has been written to '{csv_file2}'.")

data_list3 = []

sens_data3 = {
    'TAC': m.TAC(),
    'CAPEX': m.CAPEX(),
    'OPEX': m.OPEX(),
    'Revenue': m.Profit(),
    'CAPEX_FAN': m.CAPEX_FAN(),
    'OPEX_FAN': m.OPEX_FAN(),
    'N_fan': m.N_fan(),
    'Fan_Power': m.power_fan1()*m.y_f['f1']() + m.power_fan2()*m.y_f['f2']()+m.power_fan3()*m.y_f['f3'](),
    'CAPEX_H2': m.CAPEX_AEL()+m.CAPEX_SOEL()+m.CAPEX_PEMEL(),
    'OPEX_H2': m.OPEX_AEL()+m.OPEX_SOEL()+m.OPEX_PEMEL(),
    'CAPEX_DFM': m.CAPEX_DFM(),
    'Q_DFM': m.Q_DFM(),
    'N_react': m.N_react(),
    'S_react': m.S_react(),
    'v': m.v(),
    'D': m.D(),
    'L': m.L(),
    'DP': m.DP(),
    'DFM_Weight': m.DFM_Weight(),
    'k_ads': k_ads,
    'Ri': Ri,
    'q_dfm_eq': q_dfm_eq,
    'CAPEX_Boiler': m.CAPEX_Boiler(),
    'A_Boiler': m.A_Boiler(),
    'Revenue_Steam': m.Profit_Steam(),
    }
data_list3.append(sens_data3)
# Define the CSV file name
csv_file3 = 'sensitivity_output3.csv'

# Write the data to a CSV file
with open(csv_file3, mode='w', newline='') as file:
    fieldnames = ['TAC', 'CAPEX', 'OPEX', 'Revenue', 
                  'CAPEX_FAN', 'OPEX_FAN', 'N_fan', 'Fan_Power',
                  'CAPEX_H2', 'OPEX_H2',
                  'CAPEX_DFM', 'Q_DFM', 'N_react', 'S_react', 'v', 'D', 'L', 'DP', 'DFM_Weight', 'k_ads', 'Ri', 'q_dfm_eq',
                  'CAPEX_Boiler', 'A_Boiler', 'Revenue_Steam'
                  ]
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data_list3)

# Print a message to indicate that the data has been written to the CSV file
print(f"Data has been written to '{csv_file3}'.")
