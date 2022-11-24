"""Configuration of web site"""
import os

# Setup api url
MIMER_API_URL = os.getenv("MIMER_API_URL", "http://api:8000")

# Session secret key
SECRET_KEY = b"not-so-secret"

# Antibiotic classes
ANTIBIOTIC_CLASSES = {
    "Aminoglycosides": ["Amikacin", "Arbekacin", "Dibekacin", "Gentamicin", "Isepamicin", "Kanamycin", "Micronomicin", "Neomycin", "Netilmicin", "Plazomicin", "Ribostamycin", "Sisomicin", "Streptomycin", "Tobramycin"],
    "Penicillins": ["Amoxicillin", "Ampicillin", "Azlocillin", "Bacampicillin", "Benzathine benzylpenicillin", "Benzylpenicillin", "Clometocillin", "Cloxacillin", "Dicloxacillin", "Flucloxacillin", "Mecillinam", "Mezlocillin", "Nafcillin", "Oxacillin", "Penamecillin", "Pheneticillin", "Phenoxymethylpenicillin", "Piperacillin", "Pivampicillin", "Pivmecillinam", "Procaine benzylpenicillin", "Sulbenicillin"], 
    "Beta-lactam + inhibitor": ["Amoxicillin+clavulanic Acid", "Ampicillin/sulbactam", "Sultamicillin", "Piperacillin+tazobactam"], 
    "Macrolides": ["Azithromycin", "Clarithromycin", "Dirithromycin", "Erythromycin", "Josamycin", "Lincomycin", "Midecamycin", "Oleandomycin", "Roxithromycin", "Spiramycin", "Telithromycin"], 
    "Monobactams": ["Aztreonam"], 
    "Carbapenems": ["Biapenem", "Doripenem", "Ertapenem", "Imipenem", "Imipenem/cilastatin", "Meropenem", "Meropenem-vaborbactam", "Panipenem", "Tebipenem"], 
    "Carboxypenicillins": ["Carbenicillin", "Temocillin", "Ticarcillin"], 
    #"1st-gen cephalosporins": ["Cefacetrile", "Cefadroxil", "Cefalexin", "Cefalotin", "Cefapirin", "Cefatrizine", "Cefazedone", "Cefazolin", "Cefradine", "Cefroxadine", "Ceftezole"], 
    #"2nd-gen cephalosporins": ["Cefaclor", "Cefamandole", "Cefbuperazone", "Cefmetazole", "Cefminox", "Cefonicid", "Ceforanide", "Cefotetan", "Cefotiam", "Cefotiam hexetil", "Cefoxitin", "Cefprozil", "Cefuroxime", "Flomoxef"], 
    #"3rd-gen cephalosporins": ["Cefcapene pivoxil", "Cefdinir", "Cefditoren pivoxil", "Cefetamet pivoxil", "Cefixime", "Cefmenoxime", "Cefodizime", "Cefoperazone", "Cefotaxime", "Cefpiramide", "Cefpodoxime proxetil", "Ceftazidime", "Ceftazidime-avibactam", "Cefteram pivoxil", "Ceftibuten", "Ceftizoxime", "Ceftriaxone", "Latamoxef"], 
    #"4th-gen cephalosporins": ["Cefepime", "Cefoselis", "Cefozopran", "Cefpirome"], 
    #"5th-gen cephalosporins": ["Ceftaroline fosamil", "Ceftobiprole medocaril", "Ceftolozane-tazobactam"], 
    "Cephalosporins": ["Cefcapene pivoxil", "Cefdinir", "Cefditoren pivoxil", "Cefetamet pivoxil", "Cefixime", "Cefmenoxime", "Cefodizime", "Cefoperazone", "Cefotaxime", "Cefpiramide", "Cefpodoxime proxetil", "Ceftazidime", "Ceftazidime-avibactam", "Cefteram pivoxil", "Ceftibuten", "Ceftizoxime", "Ceftriaxone", "Latamoxef", "Cefaclor", "Cefamandole", "Cefbuperazone", "Cefmetazole", "Cefminox", "Cefonicid", "Ceforanide", "Cefotetan", "Cefotiam", "Cefotiam hexetil", "Cefoxitin", "Cefprozil", "Cefuroxime", "Flomoxef", "Cefacetrile", "Cefadroxil", "Cefalexin", "Cefalotin", "Cefapirin", "Cefatrizine", "Cefazedone", "Cefazolin", "Cefradine", "Cefroxadine", "Ceftezole", "Cefepime", "Cefoselis", "Cefozopran", "Cefpirome", "Ceftaroline fosamil", "Ceftobiprole medocaril", "Ceftolozane-tazobactam"], 
    "Amphenicols": ["Chloramphenicol", "Thiamphenicol"], 
    "Tetracyclines": ["Chlortetracycline", "Doxycycline", "Eravacycline", "Lymecycline", "Metacycline", "Minocycline (IV)", "Minocycline (oral)", "Omadacycline", "Oxytetracycline", "Tetracycline"], 
    "Fluoroquinolones": ["Ciprofloxacin", "Delafloxacin", "Enoxacin", "Fleroxacin", "Flumequine", "Garenoxacin", "Gatifloxacin", "Gemifloxacin", "Levofloxacin", "Lomefloxacin", "Moxifloxacin", "Norfloxacin", "Ofloxacin", "Pazufloxacin", "Pefloxacin", "Prulifloxacin", "Rufloxacin", "Sitafloxacin", "Sparfloxacin", "Tosufloxacin"], 
    "Lincosamides": ["Clindamycin"], 
    "Phenol derivatives": ["Clofoctol"], 
    "Polymyxins": ["Colistin", "Polymyxin B"], 
    "Glycopeptides": ["Dalbavancin", "Oritavancin", "Teicoplanin", "Telavancin", "Vancomycin (IV)", "Vancomycin (oral)"], 
    "Streptogramins": ["Dalfopristin-quinupristin", "Pristinamycin"], 
    "Lipopeptides": ["Daptomycin"], 
    "Penems": ["Faropenem"], 
    "Phosphonics": ["Fosfomycin (IV)", "Fosfomycin (oral)"],
    "Steroid antibacterials": ["Fusidic Acid"],
    "Oxazolidinones": ["Linezolid", "Tedizolid"], 
    "Imidazoles": ["Metronidazole (IV)", "Metronidazole (oral)"], 
    "Nitrofurantoin": ["Nitrofurantoin"], 
    "Rifamycins": ["Rifabutin", "Rifampicin", "Rifamycin", "Rifaximin"], 
    "Aminocyclitols": ["Spectinomycin"], 
    "Combination of antibiotics": ["Spiramycin/metronidazole"], 
    "Trimethoprim - sulfonamide combinations": ["Sulfadiazine/trimethoprim", "Sulfamethizole/trimethoprim", "Sulfamethoxazole/trimethoprim", "Sulfametrole/trimethoprim", "Sulfamoxole/trimethoprim"],
    "Glycylcyclines": ["Tigecycline"], 
    "Trimethoprim": ["Trimethoprim"]
}