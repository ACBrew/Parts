from ..models import Parts
from django.db import connection
from .adeo import Adeo
from .auto_rus import AutoRus
from .autoeuro import AutoEuro
from .autotrade import AutoTrade
from .berg import Berg
from .exist import Exist
from .favorit_parts import FavoritParts
from .ixora_auto import IxoraAuto
from .m_parts import M_Parts
from .next_auto import NextAuto
from .partkom import PartKom
from .rossko import Rossko
from .st_parts import STParts
import datetime
from concurrent.futures import ThreadPoolExecutor
import logging
import requests
pars = [
    # Adeo,                 # complete
    # AutoRus,              # complete
    # AutoEuro,             # complete
    # AutoTrade,            # fate is not determined
    # Berg,                 # complete
    # Exist,                # complete
    # FavoritParts,         # complete
    # IxoraAuto,            # complete
    # M_Parts,              # complete
    NextAuto,             # complete
    # PartKom,              # complete
    # Rossko,               # complete
    # STParts               # complete
    ]



def save_results(finis):
    """Сохраняет результаты парсинга сайтов в базу данных Parts, удаляя перед этим все имеющиеся в таблице данные
    """
    result = []
    # условие для возможности тестирования каждого парсера по отдельности
    if len(pars) > 1:
        with ThreadPoolExecutor(5) as p:
            p.map(lambda x: result.extend(x(finis).run()), pars)
    else:
        for i in pars:
            result += i(finis).run()
    Parts.objects.all().delete()
    with connection.cursor() as c:
        # try:
        #     c.execute("""ALTER TABLE parsers_parts AUTO_INCREMENT = 1""")
        try:
            c.execute("""DELETE FROM sqlite_sequence WHERE NAME='parsers_parts'""")
        except:
            pass



    Parts.objects.bulk_create(Parts(**val) for val in result)
    print(f'Received number of offers: {Parts.objects.all().count()}')
    return
