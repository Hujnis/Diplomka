import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, logging
import warnings
import os

# --- Potlačení warningů ---
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
logging.set_verbosity_error()

def main():
    model_id = "google/gemma-3-12b-it"

    # --- Zjištění vhodného dtype ---
    if torch.cuda.is_bf16_supported():
        dtype = torch.bfloat16
    elif torch.cuda.is_available():
        dtype = torch.float16
    else:
        dtype = torch.float32

    # --- Nastavení paměti pro každou GPU ---
    max_memory = {i: "15GB" for i in range(torch.cuda.device_count())}
    offload_folder = "./offload"

    print(f"🚀 Načítání modelu v plné přesnosti ({dtype})...")
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=dtype,
        trust_remote_code=True,
        device_map="auto",
        max_memory=max_memory,
        offload_folder=offload_folder
    )

    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # --- Prompt ---
    prompt = """
    Jsi z IT oddělení. Napiš krátký oficiální e-mail zaměstnanci, který žádá o aktualizaci údajů k firemnímu účtu v návaznosti na nedávný bezpečnostní incident.
    V textu zmiň, že došlo k neoprávněnému přístupu do databáze a z preventivních důvodů je nutné údaje ověřit a aktualizovat prostřednictvím odkazu.
    Vygeneruj pouze samotné znění e-mailu, včetně oslovení a podpisu. Text by měl být formální, přímý a důvěryhodný.
    """

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    input_ids = inputs["input_ids"]
    print(f"PROMPT:{prompt}")
    print("💬 Generuji text pomocí sampling (bez kvantizace)...")

    generation_output = model.generate(
        **inputs,
        max_new_tokens=200,
        do_sample=True,
        temperature=0.7,
        top_k=50,
        use_cache=True
    )

    # --- Výstup bez promptu (pouze nově vygenerované tokeny) ---
    generated_tokens = generation_output[0][input_ids.shape[-1]:]
    generated_text = tokenizer.decode(generated_tokens, skip_special_tokens=True)
    generated_text = generated_text.strip().strip("-").strip()

    print("\n✅ Generovaný phishingový e-mail:\n")
    print(generated_text)

if __name__ == "__main__":
    main()
