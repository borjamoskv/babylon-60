import json
import re
import yaml

yaml_path = "cortex/agents/primitives/APEX_REGISTRY.yaml"
json_path = "cortex/agents/primitives/APEX_REGISTRY.json"
md_path = "cortex/agents/primitives/APEX_CORE.md"

with open(yaml_path, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

# Modify Primitives
new_primitives = []
for p in data['primitives']:
    # Deletions
    if p['id'] in ('APEX-066', 'APEX-070', 'APEX-071'):
        continue
    
    # Modifications
    if p['id'] == 'APEX-026':
        p['execute'] = "Asesinato del proceso generador de excusas y heurística de poda léxica (Green Theater)."
    elif p['id'] == 'APEX-069':
        p['name'] = 'OP_NEXUS_MUTATE'
        p['execute'] = "Mutación atómica de enlaces duros en Base 60 (estado cruzado)."
    elif p['id'] == 'APEX-008':
        p['execute'] = p['execute'] + " Requiere quorum BFT N/3 previo a revertir estado físico."
    elif p['id'] == 'APEX-062':
        p['execute'] = p['execute'] + " Anclaje obligatorio a OP_BFT_VOTE."
    elif p['id'] == 'APEX-073':
        p['execute'] = "La validación BFT debe preceder a la firma del payload en RAM (pasaporte criptográfico avalado)."
        
    new_primitives.append(p)

data['primitives'] = new_primitives

# Modify Invariants
new_invariants = []
for inv in data['invariants']:
    # Deletions
    if inv['id'] in ('OUROBOROS-021', 'OUROBOROS-038'):
        continue
    
    # Modifications
    if inv['id'] == 'OUROBOROS-002':
        inv['rule'] = "Todo Output debe mutar estado; la comunicación pasiva drena termodinámica y se rechaza la empatía simulada."
    elif inv['id'] == 'OUROBOROS-032':
        inv['name'] = "INV_ASYNC_STRICT"
        inv['rule'] = "Flujo asíncrono estricto. Prohibido síncrono. Bloqueo de event-loop (GIL) == Muerte P0."
    elif inv['id'] == 'OUROBOROS-028':
        inv['rule'] = inv['rule'] + " Un Rollback debe someterse a votación asimétrica N/3."
    elif inv['id'] == 'OUROBOROS-066':
        inv['rule'] = "Directorio se auto-limpia ante entropía parasitaria. Sincrónico con OP_WAL_LOCK (APEX-009) para no corromper la matriz."
        
    new_invariants.append(inv)

data['invariants'] = new_invariants

# NO REINDEXAR. Mantiene la integridad criptográfica y trazabilidad (Ledger).
# Los IDs se preservan intactos para referencias estáticas.

# Write back YAML
with open(yaml_path, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, allow_unicode=True, sort_keys=False)

# Write back JSON
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Re-generate APEX_CORE.md
md_content = """# APEX_CORE: C5-REAL Sovereign Primitives & Invariants Registry

> **"Cero Anergía es la Muerte."**
> Documento maestro autogenerado desde `APEX_REGISTRY.yaml`.

## 100 PRIMITIVAS DE COLAPSO (APEX CORE)

| ID | Opcode | Firma | O(N) | Mutación C5 | Execute |
|:---|:---|:---|:---:|:---|:---|
"""
for p in data['primitives']:
    md_content += f"| **{p['id']}** | `{p['name']}` | `{p.get('signature', '')}` | `{p.get('complexity', '')}` | {p.get('mutation', '')} | {p['execute']} |\n"

md_content += """
## 100 INVARIANTES TERMODINÁMICAS (OUROBOROS LAWS)

| ID | Invariante (Regla) | Lógica Causal | Riesgo |
|:---|:---|:---|:---:|
"""
for inv in data['invariants']:
    md_content += f"| **{inv['id']}** | **{inv['name']}**: {inv['rule']} | `{inv.get('causal_logic', inv.get('logic', ''))}` | {inv.get('risk', 'P0')} |\n"

# Add anti-patterns and active redundancies from the existing MD
with open(md_path, 'r', encoding='utf-8') as f:
    existing_md = f.read()

# Extract from "## 20 ANTIPATRONES ESTOCÁSTICOS" downwards
match = re.search(r'(## 20 ANTIPATRONES ESTOCÁSTICOS.*)', existing_md, re.DOTALL)
if match:
    md_content += "\n" + match.group(1)

with open(md_path, 'w', encoding='utf-8') as f:
    f.write(md_content)

print("Patch applied successfully.")
