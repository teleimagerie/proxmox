#!/usr/bin/env python3
"""
Enrolement TOTP propre : repart toujours d'une table rase, ne laisse
jamais deux secrets coexister, et ne valide qu'apres verification.

A lancer depuis VOTRE terminal :
    ssh -t root@pve1.infra.teleimagerie.net 'python3 /root/enroll-totp.py matt@pve'
"""
import base64
import hashlib
import hmac
import json
import os
import struct
import subprocess
import sys
import time

user = sys.argv[1] if len(sys.argv) > 1 else "matt@pve"


def existing(u):
    try:
        return json.load(open("/etc/pve/priv/tfa.cfg"))["users"].get(u, {})
    except Exception:
        return {}


def totp_code(secret, when=None):
    key = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8))
    h = hmac.new(key, struct.pack(">Q", int((when or time.time()) // 30)),
                 hashlib.sha1).digest()
    o = h[19] & 0xF
    return f"{(struct.unpack('>I', h[o:o + 4])[0] & 0x7FFFFFFF) % 1000000:06d}"


print(f"\n{'=' * 62}\n  Enrolement TOTP pour {user}\n{'=' * 62}\n")

# --- 1. Table rase : aucun secret residuel ne doit survivre -------------
if existing(user):
    print("Des entrees TFA existent deja. Elles vont etre TOUTES supprimees")
    print("pour garantir qu'un seul secret subsiste a la fin.\n")
    if input("Continuer ? [o/N] ").strip().lower() not in ("o", "oui", "y"):
        sys.exit("Abandon, rien n'a ete modifie.")
    subprocess.run(["pveum", "user", "tfa", "delete", user],
                   capture_output=True, text=True)
    print("  anciennes entrees supprimees\n")

print(">>> IMPORTANT : dans Google Authenticator, supprimez maintenant TOUTES")
print(">>> les entrees 'Proxmox' existantes. Elles sont toutes perimees.\n")
input("Appuyez sur Entree une fois le telephone nettoye...")

# --- 2. Nouveau secret --------------------------------------------------
secret = base64.b32encode(os.urandom(20)).decode().rstrip("=")
uri = (f"otpauth://totp/Proxmox:{user}?secret={secret}"
       f"&issuer=Proxmox&digits=6&period=30&algorithm=SHA1")

print(f"\n{'=' * 62}\n")
try:
    subprocess.run(["qrencode", "-t", "ANSIUTF8", uri], check=True)
except Exception:
    pass
print(f"\nSaisie manuelle si le QR ne passe pas ('Saisir une cle de configuration') :")
print(f"\n    {secret}\n")
input("Scannez, puis appuyez sur Entree...")

# --- 3. Verification AVANT enregistrement -------------------------------
for essai in range(3):
    saisi = input("\nCode a 6 chiffres affiche par l'application : ").strip().replace(" ", "")
    # tolerance d'une fenetre avant/apres pour la derive d'horloge
    valides = {totp_code(secret, time.time() + d) for d in (-30, 0, 30)}
    if saisi in valides:
        print("  code correct, le telephone et le serveur sont synchronises")
        break
    print(f"  code incorrect (tentative {essai + 1}/3) - attendez le code suivant")
else:
    sys.exit("\nAbandon : le secret n'a pas ete correctement transfere. "
             "Aucun TFA n'a ete active, la connexion par mot de passe reste possible.")

# --- 4. Enregistrement --------------------------------------------------
r = subprocess.run(
    ["pvesh", "create", f"/access/tfa/{user}", "--type", "totp",
     "--description", f"Authenticator ({time.strftime('%d/%m/%Y')})",
     "--totp", uri, "--value", totp_code(secret)],
    capture_output=True, text=True)
if r.returncode != 0:
    sys.exit(f"ECHEC de l'enregistrement : {r.stderr.strip()}")

n = len(existing(user).get("totp", []))
print(f"\nTOTP active. Entrees TOTP enregistrees : {n} (doit valoir 1)")

# --- 5. Cles de secours -------------------------------------------------
print(f"\n{'=' * 62}")
print("  CLES DE SECOURS - notez-les MAINTENANT, elles ne seront")
print("  plus jamais affichables. Une seule utilisation chacune.")
print("  A conserver ailleurs que sur le telephone.")
print(f"{'=' * 62}")
subprocess.run(["pvesh", "create", f"/access/tfa/{user}", "--type", "recovery"])
print(f"{'=' * 62}")
print("\nTestez la connexion dans un AUTRE navigateur avant de fermer ce terminal.")
print(f"En cas de blocage : ssh root@... 'pveum user tfa delete {user}'\n")
