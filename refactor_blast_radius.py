import os
from pathlib import Path

def refactor_blast_radius():
    # --- babylon60 ---
    filepath = Path("/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/babylon60/engine/blast_radius.py")
    content = filepath.read_text(encoding="utf-8")
    
    # Imports
    content = content.replace("import subprocess", "import subprocess\nfrom decimal import Decimal")
    
    # __init__ and fields
    old_init = """    __slots__ = ("hourly_rate", "token_cost_per_m")

    def __init__(self, hourly_rate: float = 150.0) -> None:
        self.hourly_rate = hourly_rate
        self.token_cost_per_m = 0.015

    def calculate_hours_saved(self, commits: int, lines_added: int, lines_deleted: int) -> Babylon60:
        \"\"\"Calculate hours saved based strictly on physical git mutations (Ω₂).\"\"\"
        minutes = (commits * 15.0) + (lines_added * 2.0) + (lines_deleted * 1.0)
        return round(minutes / 60.0, 2)"""
    new_init = """    __slots__ = ("hourly_rate", "token_cost_per_m")

    def __init__(self, hourly_rate: 'Babylon60 | None' = None) -> None:
        self.hourly_rate = hourly_rate or Babylon60(32400000)  # 150 * 216000
        self.token_cost_per_m = Babylon60(3240)  # 0.015 * 216000

    def calculate_hours_saved(self, commits: int, lines_added: int, lines_deleted: int) -> 'Babylon60':
        \"\"\"Calculate hours saved based strictly on physical git mutations (Ω₂).\"\"\"
        minutes = (commits * 15) + (lines_added * 2) + (lines_deleted * 1)
        return Babylon60(minutes * 3600)"""
    
    content = content.replace(old_init, new_init)
    
    old_calc = """        # C5-REAL: Exergy is measured directly from physical mutations, not arbitrary complexity.
        hours = self.calculate_hours_saved(git["commits"], git["added"], git["deleted"])
        monetary_value = round(hours * self.hourly_rate, 2)"""
    new_calc = """        # C5-REAL: Exergy is measured directly from physical mutations, not arbitrary complexity.
        hours = self.calculate_hours_saved(git["commits"], git["added"], git["deleted"])
        monetary_value = hours * self.hourly_rate"""
        
    content = content.replace(old_calc, new_calc)
    
    old_cost = """        cost = (final_tokens / 1000.0) * self.token_cost_per_m
        roi_ratio = monetary_value / max(0.001, cost)"""
    new_cost = """        cost_value = (final_tokens * self.token_cost_per_m.value) // 1000
        cost = Babylon60(cost_value)
        if cost.value <= 216:
            cost = Babylon60(216)
        roi_ratio = monetary_value / cost"""
        
    content = content.replace(old_cost, new_cost)
    filepath.write_text(content, encoding="utf-8")
    
    # --- cortex ---
    filepath = Path("/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/engine/blast_radius.py")
    content = filepath.read_text(encoding="utf-8")
    
    content = content.replace("import subprocess", "import subprocess\nfrom decimal import Decimal")
    
    old_init_cortex = """    __slots__ = ("hourly_rate", "token_cost_per_m")

    def __init__(self, hourly_rate: float = 150.0) -> None:
        self.hourly_rate = hourly_rate
        self.token_cost_per_m = 0.015

    def calculate_hours_saved(self, commits: int, lines_added: int, lines_deleted: int) -> float:
        \"\"\"Calculate hours saved based strictly on physical git mutations (Ω₂).\"\"\"
        minutes = (commits * 15.0) + (lines_added * 2.0) + (lines_deleted * 1.0)
        return round(minutes / 60.0, 2)"""
    new_init_cortex = """    __slots__ = ("hourly_rate", "token_cost_per_m")

    def __init__(self, hourly_rate: Decimal | None = None) -> None:
        self.hourly_rate = hourly_rate or Decimal("150.0")
        self.token_cost_per_m = Decimal("0.015")

    def calculate_hours_saved(self, commits: int, lines_added: int, lines_deleted: int) -> Decimal:
        \"\"\"Calculate hours saved based strictly on physical git mutations (Ω₂).\"\"\"
        minutes = (commits * 15) + (lines_added * 2) + (lines_deleted * 1)
        return round(Decimal(minutes) / Decimal(60), 2)"""
        
    content = content.replace(old_init_cortex, new_init_cortex)
    
    old_calc_cortex = """        # C5-REAL: Exergy is measured directly from physical mutations, not arbitrary complexity.
        hours = self.calculate_hours_saved(git["commits"], git["added"], git["deleted"])
        monetary_value = round(hours * self.hourly_rate, 2)"""
    new_calc_cortex = """        # C5-REAL: Exergy is measured directly from physical mutations, not arbitrary complexity.
        hours = self.calculate_hours_saved(git["commits"], git["added"], git["deleted"])
        monetary_value = round(hours * self.hourly_rate, 2)"""
        
    content = content.replace(old_calc_cortex, new_calc_cortex)
    
    old_cost_cortex = """        cost = (final_tokens / 1000.0) * self.token_cost_per_m
        roi_ratio = monetary_value / max(0.001, cost)"""
    new_cost_cortex = """        cost = (Decimal(final_tokens) / Decimal(1000)) * self.token_cost_per_m
        min_cost = Decimal("0.001")
        actual_cost = cost if cost > min_cost else min_cost
        roi_ratio = round(monetary_value / actual_cost, 2)"""
        
    content = content.replace(old_cost_cortex, new_cost_cortex)
    
    # Also fix ChronosReport definition in cortex
    old_report = """    hours_saved: float
    money_saved: float
    roi_ratio: float
    cost: float"""
    new_report = """    hours_saved: Decimal
    money_saved: Decimal
    roi_ratio: Decimal
    cost: Decimal"""
    content = content.replace(old_report, new_report)
    
    filepath.write_text(content, encoding="utf-8")

if __name__ == "__main__":
    refactor_blast_radius()
