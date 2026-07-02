from pathlib import Path


class AnalystAgent:
    def run(self, state):
        feature_mappings = {
            "auth": "authentication",
            "login": "authentication",
            "payment": "payments",
            "checkout": "payments",
            "agent": "agent_system",
            "chat": "messaging",
            "message": "messaging",
        }

        for file in state.files[:100]:
            try:
                content = Path(file).read_text(errors="ignore")[:3000]
                state.summaries[file] = content
                lc = content.lower()

                matched_features = {
                    feat for kw, feat in feature_mappings.items() if kw in lc
                }
                for feat in matched_features:
                    state.features.append({"feature": feat, "source": file})

                if "todo" in lc:
                    state.technical_debt.append({"type": "TODO_found", "file": file})

            except Exception:
                continue

        return state
