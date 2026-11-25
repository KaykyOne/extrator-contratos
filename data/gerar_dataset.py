"""Gera 24 registros anotados à mão. Todos os dados são fictícios."""
import json
from pathlib import Path

# Cada tupla fornece o estilo, o texto e o gabarito. As chaves seguem a ordem
# abaixo para facilitar a conferência sem inferir o gabarito com o pipeline.
CAMPOS = (
    "locador", "locatario", "endereco_imovel", "valor_aluguel",
    "prazo_meses", "data_inicio", "valor_multa_rescisoria", "indice_reajuste",
)

REGISTROS = (
    ("formal", "Locador: Edravo de Lumeflor; locatária: Nélida de Vazul. "
     "Imóvel: Rua Nimbo de Mel, 41. Aluguel mensal de R$ 1.450,00. Prazo de 24 meses. "
     "Início da vigência em 01/03/2031. Multa rescisória de R$ 2.900,00. Reajuste pelo IPCA.",
     ("Edravo de Lumeflor", "Nélida de Vazul", "Rua Nimbo de Mel, 41", 1450, 24, "2031-03-01", 2900, "IPCA")),
    ("formal", "Locadora: Naira de Marfinéu. Locatário: Tomélio de Azulvão. Imóvel situado na Avenida "
     "Serra de Vidro, 317. Aluguel de R$ 2.340,70; prazo de 2 anos; vigência em 2032-07-01. "
     "Multa por rescisão: R$ 3.000,00; reajuste anual pelo IGP-M.",
     ("Naira de Marfinéu", "Tomélio de Azulvão", "Avenida Serra de Vidro, 317", 2340.70, 24, "2032-07-01", 3000, "IGP-M")),
    ("formal", "São partes deste instrumento Sávio de Miralva, locador, e Cíntala de Nebrisol, "
     "locatária. Endereço do imóvel: Travessa da Areia Doce, 15. Aluguel mensal: R$ 810,00. "
     "Início: 05/10/2030. Prazo de 6 meses. Reajuste por INPC.",
     ("Sávio de Miralva", "Cíntala de Nebrisol", "Travessa da Areia Doce, 15", 810, 6, "2030-10-05", None, "INPC")),
    ("formal", "Locador: Oresto de Tamarivento; locatária: Dalúna de Pendral. "
     "Imóvel: Alameda Gota de Bronze, 52. Assinatura: 22/11/2031. Vigência a partir de 01/12/2031. "
     "Caução R$ 3.600,00; aluguel de R$ 1.200,00; multa por atraso de R$ 80,00; prazo de 18 meses.",
     ("Oresto de Tamarivento", "Dalúna de Pendral", "Alameda Gota de Bronze, 52", 1200, 18, "2031-12-01", None, None)),
    ("informal", "Cevina de Umbrafim é a proprietária; Ruvano de Solvedra vai morar na Rua Folha de "
     "Prata, 18. Ele paga 980 reais todo mês. São 8 meses começando no dia 02/05/2032.",
     ("Cevina de Umbrafim", "Ruvano de Solvedra", "Rua Folha de Prata, 18", 980, 8, "2032-05-02", None, None)),
    ("informal", "Proprietário: Mirolo de Salnuvem. Inquilina: Vília de Laranéu. Endereço: Rua Pedra "
     "de Farinha, 500. O aluguel é R$ 1150,50 por 10 meses. Começa em 09/01/2030. "
     "Se sair antes, paga R$ 575,25. Reajuste pelo IPCA.",
     ("Mirolo de Salnuvem", "Vília de Laranéu", "Rua Pedra de Farinha, 500", 1150.50, 10, "2030-01-09", 575.25, "IPCA")),
    ("informal", "Locadora: Dália de Trisnuvem. Locatário: Tevino de Miracobre. Imóvel: Avenida "
     "Estrela Rasa, 73. Aluguel de R$ 700,00. O trato vale por um semestre; a chave entra no dia "
     "primeiro de agosto de 2032, quando a locação começa.",
     ("Dália de Trisnuvem", "Tevino de Miracobre", "Avenida Estrela Rasa, 73", 700, 6, "2032-08-01", None, None)),
    ("informal", "A dona, Norélia de Ventaclara, aluga a casa para Belivo de Pedracinza. "
     "Imóvel: Estrada do Sol de Inverno, 950. Pagamento mensal de R$ 680,00; prazo de 3 meses. "
     "Se rescindir antes do prazo, fica explicitamente dispensada qualquer multa.",
     ("Norélia de Ventaclara", "Belivo de Pedracinza", "Estrada do Sol de Inverno, 950", 680, 3, None, 0, None)),
    ("whatsapp", "[08:41] Lúnio de Rosavento: sou o dono e vou alugar o apê pra você, "
     "Tévia de Lagoazul. É na Rua Amanhecer de Gelo, 28.\n[08:42] Lúnio: fechamos 1350 reais/mês "
     "por 12 meses?\n[08:43] Tévia: fechado, começa em 04/04/2033 😊",
     ("Lúnio de Rosavento", "Tévia de Lagoazul", "Rua Amanhecer de Gelo, 28", 1350, 12, "2033-04-04", None, None)),
    ("whatsapp", "✅ locador = Clévio de Azulmusgo\n✅ inquilina = Rúbia de Névoamar\n"
     "imóvel: Praça dos Relógios de Areia, 66\naluguel: R$ 925,00\nprazo: 9 meses\ninício: 17/02/2031\n"
     "reajuste: IPCA",
     ("Clévio de Azulmusgo", "Rúbia de Névoamar", "Praça dos Relógios de Areia, 66", 925, 9, "2031-02-17", None, "IPCA")),
    ("whatsapp", "Olá, Lévina de Licorvento! Aqui é o proprietário, Orvélio de Miranil. Você será "
     "a inquilina. Pra confirmar: Av. Miragem de Cera, 107, R$ 1.800,00 de aluguel por mês. "
     "Se romper antes, são dois aluguéis de multa.",
     ("Orvélio de Miranil", "Lévina de Licorvento", "Av. Miragem de Cera, 107", 1800, None, None, 3600, None)),
    ("whatsapp", "chat do aluguel\nlocadora: Numi de Arealuz\nlocatário: Vitorno de Virabruma\n"
     "imóvel: Rua Pingo de Sal, 81\naluguel R$ 660,00\nprazo: 4 meses\n"
     "começa em 12/06/2034\nna quebra antes do prazo: multa de R$ 200,00.",
     ("Numi de Arealuz", "Vitorno de Virabruma", "Rua Pingo de Sal, 81", 660, 4, "2034-06-12", 200, None)),
    ("bagunçado", "RASCUNHO ### aluguel: R$ 2.050,00; INÍCIO=06/08/2030\n"
     "LOCATÁRIO - Arvelo de Ventanil\nLOCADOR - Bêlina de Noiteluz\n"
     "imóvel=Rua Sopro de Âmbar, 4\nprazo=15 meses\nMULTA RESCISÓRIA=R$ 1.025,00\nreajuste=IGP-M",
     ("Bêlina de Noiteluz", "Arvelo de Ventanil", "Rua Sopro de Âmbar, 4", 2050, 15, "2030-08-06", 1025, "IGP-M")),
    ("bagunçado", "cópia\nprazo de 11 meses / assinatura 2034-03-03\nlocatária: Nelusa de Ventorrio\n"
     "endereço: Alameda Cálamo de Nuvem, 16\nlocador: Mávio de Fulgorazul\n"
     "multa por rescisão antecipada de R$ 500,00\naluguel: R$ 990,00\nINÍCIO 2034-05-19",
     ("Mávio de Fulgorazul", "Nelusa de Ventorrio", "Alameda Cálamo de Nuvem, 16", 990, 11, "2034-05-19", 500, None)),
    ("bagunçado", "rótulos trocados no papel: a mora é R$ 70,00; o sinal é R$ 2.000,00. "
     "corrigido: aluguel R$ 1.000,00; imóvel: Rua Espuma de Sol, 24. Locador: Ilauro de "
     "Verdebreu; locatário: Seravo de Dourasombra. Prazo: 20 meses. Reajuste anual pelo IPC-FIPE.",
     ("Ilauro de Verdebreu", "Seravo de Dourasombra", "Rua Espuma de Sol, 24", 1000, 20, None, None, "IPC-FIPE")),
    ("bagunçado", "Imóvel: Travessa Eco de Quartzo, 85\nLOCADORA: Ylina de Brumaluz\n"
     "R$ 1.325,00 por mês!!!\nInquilino: Ávoro de Maravento\n"
     "prazo 14 meses; vigência 13/04/2032. Multa rescisória R$ 300,00.",
     ("Ylina de Brumaluz", "Ávoro de Maravento", "Travessa Eco de Quartzo, 85", 1325, 14, "2032-04-13", 300, None)),
    ("ausências", "Locador: Brevânio de Azulturvo. Locatária: Ninela de Pontalume. "
     "O aluguel mensal de R$ 870,00 será pago dia 5. Assinatura em 08/04/2030.",
     ("Brevânio de Azulturvo", "Ninela de Pontalume", None, 870, None, None, None, None)),
    ("ausências", "Locatário: Lúvero de Selvanil. Endereço: Rua Flor de Chumbo, 53. "
     "Prazo de 3 meses. As partes vão negociar o valor e o início posteriormente.",
     (None, "Lúvero de Selvanil", "Rua Flor de Chumbo, 53", None, 3, None, None, None)),
    ("ausências", "Imóvel: Alameda Soprafolha, 11. O aluguel será de R$ 760,00. "
     "A rescisão antecipada será isenta de multa. Reajuste pelo INPC.",
     (None, None, "Alameda Soprafolha, 11", 760, None, None, 0, "INPC")),
    ("ausências", "Locadora: Lóvina de Zafiréu. O contrato começa em 14/06/2035. "
     "O prazo é indeterminado. Índice, valores, endereço e ocupante ainda serão definidos.",
     ("Lóvina de Zafiréu", None, None, None, None, "2035-06-14", None, None)),
    ("por extenso", "Locador: Venílio de Pedramar. Locatária: Mérula de Cedronévoa. "
     "Imóvel: Rua Abóbada de Algodão, 29. Aluguel de dois mil e quinze reais e cinquenta centavos "
     "pelo prazo de quinze meses. Início: 01/11/2031. Reajuste pelo IPCA.",
     ("Venílio de Pedramar", "Mérula de Cedronévoa", "Rua Abóbada de Algodão, 29", 2015.50, 15, "2031-11-01", None, "IPCA")),
    ("por extenso", "Proprietária: Célora de Açucenil. Locatário: Deruno de Nuvampoa. "
     "Endereço: Rua Agulha de Orvalho, 81. Aluguel mensal de setecentos e oitenta reais por dois anos. "
     "A vigência começa em dez de janeiro de 2032. Multa rescisória de mil e quinhentos reais.",
     ("Célora de Açucenil", "Deruno de Nuvampoa", "Rua Agulha de Orvalho, 81", 780, 24, "2032-01-10", 1500, None)),
    ("por extenso", "Aluguel de novecentos e noventa e nove reais. Prazo de doze meses. "
     "Locador: Drávio de Nuvemansa; locatária: Iolusta de Jasmimneve. "
     "Imóvel: Praça Lua de Papel, 12. Multa por rescisão de um aluguel. Reajuste pelo IGP-M.",
     ("Drávio de Nuvemansa", "Iolusta de Jasmimneve", "Praça Lua de Papel, 12", 999, 12, None, 999, "IGP-M")),
    ("por extenso", "Locadora: Sílvora de Luarbreu. Inquilino: Davélio de Trispedra. "
     "Imóvel: Estrada do Vento Doce, 7. O aluguel mensal é de mil e cem reais. "
     "Por dezoito meses desde 22/03/2033. Rescisão antecipada sem multa.",
     ("Sílvora de Luarbreu", "Davélio de Trispedra", "Estrada do Vento Doce, 7", 1100, 18, "2033-03-22", 0, None)),
)


def gerar_dataset() -> None:
    """Escreve um JSON determinístico, preservando a ordem das anotações."""
    dataset = [
        {"id": f"C{numero:02}", "estilo": estilo, "texto": texto,
         "gold": dict(zip(CAMPOS, valores, strict=True))}
        for numero, (estilo, texto, valores) in enumerate(REGISTROS, start=1)
    ]
    destino = Path(__file__).with_name("dataset.json")
    destino.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    gerar_dataset()
