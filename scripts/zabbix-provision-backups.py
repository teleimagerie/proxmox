#!/usr/bin/env python3
"""Provisioning Zabbix de la supervision des sauvegardes — trace exécutable
du chantier du 30/08/2026 (17-zabbix.md § Supervision des sauvegardes).

S'exécute SUR le CT 204. Idempotent : chaque objet est cherché avant d'être
créé ; relancer ne casse rien. Jeton API Zabbix lu dans /root/.zbx-api-token
(le même que zabbix-provision-pve.py). Le secret du token PBS n'est requis
qu'à la pose des macros : variable d'environnement PBS_TOKEN_SECRET.

Objets gérés (tout vit dans le template « TIM Cluster PVE ») :
  - vzdump : 1 item maître HTTP par nœud (/nodes/{n}/tasks, typefilter
    vzdump, archive) + dépendants JavaScript : nb de tâches en échec < 26 h,
    âge du dernier succès du job quotidien (id vide — les vzdump manuels ne
    comptent pas), âge du hebdo VM 102 (id "102") replié en min() cluster ;
  - triggers High : échec < 26 h par nœud, quotidien absent > 26 h (avec
    garde nodata 3 h : un item cassé gèlerait last()), hebdo absent > 8 j ;
  - macros hôte cluster-pve : {$PBS.URL}, {$PBS.TOKEN.ID},
    {$PBS.TOKEN.SECRET} (secrète) ;
  - PBS : 3 items maîtres HTTP (garbage_collection / verificationjob /
    prunejob — le « contains » du typefilter exclut les GC/verify/prune
    manuels) + dépendants : dernier verdict, âge du dernier succès ;
  - triggers High PBS : dernier verdict <> OK (se referme au succès
    suivant), GC/verify absents > 8 j, prune absent > 26 h.

Fenêtres : job quotidien 02:00 → 26 h = 24 h + marge job lent ; hebdo
samedi 03:30 et verify/GC dimanche → 8 j ; prune quotidien 03:00 → 26 h.

Usage : zabbix-provision-backups.py {vzdump|macros|pbs|check}
"""
import json
import os
import sys
import urllib.request

API = "http://127.0.0.1:8080/api_jsonrpc.php"
TOKEN = open("/root/.zbx-api-token").read().strip()
TPL = "TIM Cluster PVE"
NODES = ("pve1", "pve2", "pve3")
PBS_TYPES = (  # worker_type PBS -> (clef, libelle, fenetre d'absence, garde nodata)
    ("garbage_collection", "gc", "garbage collection", "8d", "6h"),
    ("verificationjob", "verify", "verification", "8d", "6h"),
    ("prunejob", "prune", "prune", "26h", "6h"),
)


def zbx(method, params):
    req = urllib.request.Request(
        API,
        data=json.dumps({"jsonrpc": "2.0", "method": method, "params": params,
                         "id": 1}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {TOKEN}"})
    out = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if "error" in out:
        sys.exit(f"API {method}: {out['error']}")
    return out["result"]


def template_id():
    t = zbx("template.get", {"filter": {"host": [TPL]}})
    if not t:
        sys.exit(f"template introuvable: {TPL} (lancer zabbix-provision-pve.py d'abord)")
    return t[0]["templateid"]


def ensure_item(tid, params):
    ex = zbx("item.get", {"templateids": [tid], "filter": {"key_": [params["key_"]]}})
    return ex[0]["itemid"] if ex else zbx("item.create", {**params, "hostid": tid})["itemids"][0]


def ensure_trigger(tid, desc, expr, prio):
    if not zbx("trigger.get", {"templateids": [tid], "filter": {"description": [desc]}}):
        zbx("trigger.create", {"description": desc, "expression": expr, "priority": prio})


def js(script):
    return [{"type": 21, "params": script, "error_handler": 0, "error_handler_params": ""}]


JS_ERRORS = """var d = JSON.parse(value).data, now = Math.floor(Date.now()/1000), n = 0;
d.forEach(function (t) {
  if (!t.endtime || !t.status) return;      // tache encore en cours
  if (now - t.starttime > 26*3600) return;  // fenetre 26 h
  if (t.status !== "OK") n++;               // "WARNINGS: x" compte aussi
});
return n;"""

# id vide = tache du job planifie ; un vzdump manuel (id=vmid) ne rafraichit pas l'age
JS_AGE_JOB = """var d = JSON.parse(value).data, now = Math.floor(Date.now()/1000), last = 0;
d.forEach(function (t) {
  if (t.id !== "%s" || t.status !== "OK") return;
  if (t.endtime > last) last = t.endtime;
});
return last ? now - last : 9999999;"""

JS_PBS_STATUS = """var d = JSON.parse(value).data, best = null;
d.forEach(function (t) {
  if (!t.endtime || !t.status) return;
  if (!best || t.starttime > best.starttime) best = t;
});
return best ? best.status : "NO-TASK";"""

JS_PBS_AGE = """var d = JSON.parse(value).data, now = Math.floor(Date.now()/1000), last = 0;
d.forEach(function (t) {
  if (t.status !== "OK" || !t.endtime) return;
  if (t.endtime > last) last = t.endtime;
});
return last ? now - last : 9999999;"""


def vzdump():
    tid = template_id()
    for n in NODES:
        master = ensure_item(tid, {
            "name": f"vzdump {n}: taches brutes (API PVE)",
            "key_": f"pve.vzdump.tasks[{n}]", "type": 19, "value_type": 4,
            "delay": "10m", "history": "1d", "trends": "0",
            "url": f"https://{n}.infra.teleimagerie.net:8006/api2/json/nodes/{n}/tasks"
                   "?typefilter=vzdump&source=archive&limit=50",
            "headers": [{"name": "Authorization",
                         "value": "PVEAPIToken={$PVE.TOKEN.ID}={$PVE.TOKEN.SECRET}"}]})
        ensure_item(tid, {"name": f"vzdump {n}: taches en echec (<26 h)",
                          "key_": f"pve.vzdump.errors[{n}]", "type": 18,
                          "master_itemid": master, "value_type": 3, "delay": "0",
                          "history": "7d", "preprocessing": js(JS_ERRORS)})
        ensure_item(tid, {"name": f"vzdump {n}: age du dernier succes du job quotidien",
                          "key_": f"pve.vzdump.daily.age[{n}]", "type": 18,
                          "master_itemid": master, "value_type": 3, "units": "s",
                          "delay": "0", "history": "7d",
                          "preprocessing": js(JS_AGE_JOB % "")})
        ensure_item(tid, {"name": f"vzdump {n}: age du dernier succes du hebdo VM 102",
                          "key_": f"pve.vzdump.102.age[{n}]", "type": 18,
                          "master_itemid": master, "value_type": 3, "units": "s",
                          "delay": "0", "history": "7d",
                          "preprocessing": js(JS_AGE_JOB % "102")})
    # la VM 102 migre : l'age qui compte est le min des trois noeuds
    ensure_item(tid, {"name": "vzdump cluster: age du dernier succes hebdo VM 102",
                      "key_": "pve.vzdump.102.age", "type": 15, "value_type": 3,
                      "units": "s", "delay": "10m", "history": "7d",
                      "params": "min(" + ",".join(
                          f"last(//pve.vzdump.102.age[{n}])" for n in NODES) + ")"})

    for n in NODES:
        ensure_trigger(tid, f"{n}: tache vzdump en echec (<26 h)",
                       f'last(/{TPL}/pve.vzdump.errors[{n}])>0', 4)
        ensure_trigger(tid, f"{n}: aucune sauvegarde quotidienne reussie depuis 26 h",
                       f'last(/{TPL}/pve.vzdump.daily.age[{n}])>26h'
                       f' or nodata(/{TPL}/pve.vzdump.daily.age[{n}],3h)=1', 4)
    ensure_trigger(tid, "Cluster: sauvegarde hebdo VM 102 (nas-vm) absente depuis 8 j",
                   f'last(/{TPL}/pve.vzdump.102.age)>8d'
                   f' or nodata(/{TPL}/pve.vzdump.102.age,6h)=1', 4)
    print("vzdump OK")


def macros():
    secret = os.environ.get("PBS_TOKEN_SECRET") or sys.exit("PBS_TOKEN_SECRET absent")
    h = zbx("host.get", {"filter": {"host": ["cluster-pve"]}})
    if not h:
        sys.exit("hote cluster-pve introuvable")
    hid = h[0]["hostid"]
    have = {m["macro"] for m in zbx("usermacro.get", {"hostids": [hid]})}
    for macro, value, mtype in (
            ("{$PBS.URL}", "https://10.40.0.20:8007", "0"),
            ("{$PBS.TOKEN.ID}", "zabbix@pbs!monitoring", "0"),
            ("{$PBS.TOKEN.SECRET}", secret, "1")):
        if macro not in have:
            zbx("usermacro.create", {"hostid": hid, "macro": macro,
                                     "value": value, "type": mtype})
            print(macro, "posee")
    print("macros OK")


def pbs():
    tid = template_id()
    for wtype, key, label, window, guard in PBS_TYPES:
        master = ensure_item(tid, {
            "name": f"PBS: taches {label} brutes (API PBS)",
            "key_": f"pbs.tasks.{key}", "type": 19, "value_type": 4,
            "delay": "15m", "history": "1d", "trends": "0",
            "url": "{$PBS.URL}/api2/json/nodes/localhost/tasks"
                   f"?typefilter={wtype}&limit=20",
            # cert auto-signe de PBS : pas de verification TLS (VLAN 400 interne)
            "verify_peer": 0, "verify_host": 0,
            "headers": [{"name": "Authorization",
                         "value": "PBSAPIToken={$PBS.TOKEN.ID}:{$PBS.TOKEN.SECRET}"}]})
        ensure_item(tid, {"name": f"PBS {label}: dernier verdict",
                          "key_": f"pbs.task.{key}.last_status", "type": 18,
                          "master_itemid": master, "value_type": 4, "delay": "0",
                          "history": "7d", "trends": "0",
                          "preprocessing": js(JS_PBS_STATUS)})
        ensure_item(tid, {"name": f"PBS {label}: age du dernier succes",
                          "key_": f"pbs.task.{key}.age", "type": 18,
                          "master_itemid": master, "value_type": 3, "units": "s",
                          "delay": "0", "history": "7d",
                          "preprocessing": js(JS_PBS_AGE)})
        ensure_trigger(tid, f"PBS: derniere {label} en echec",
                       f'last(/{TPL}/pbs.task.{key}.last_status)<>"OK"', 4)
        ensure_trigger(tid, f"PBS: {label} absente depuis {window}",
                       f'last(/{TPL}/pbs.task.{key}.age)>{window}'
                       f' or nodata(/{TPL}/pbs.task.{key}.age,{guard})=1', 4)
    print("pbs OK")


def check():
    keys = [f"pve.vzdump.errors[{n}]" for n in NODES]
    keys += [f"pve.vzdump.daily.age[{n}]" for n in NODES]
    keys += ["pve.vzdump.102.age"]
    keys += [f"pbs.task.{k}.{s}" for _, k, _, _, _ in PBS_TYPES
             for s in ("last_status", "age")]
    for k in keys:
        i = zbx("item.get", {"host": "cluster-pve", "filter": {"key_": [k]},
                             "output": ["key_", "lastvalue", "lastclock"]})
        if i:
            print(f"  {i[0]['key_']} = {i[0]['lastvalue']}")
        else:
            print(f"  {k} : ITEM ABSENT")


if __name__ == "__main__":
    actions = {"vzdump": vzdump, "macros": macros, "pbs": pbs, "check": check}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        sys.exit(__doc__)
    actions[sys.argv[1]]()
