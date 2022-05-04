import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
import random
from typing import Set

from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.data import Difficulty, Race
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.main import run_game
from sc2.player import Bot, Computer
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class unidosDaEc(BotAI):

    def __init__(self):
        self.distance_calculation_method = 3
    
    async def on_step(self, iteration):
        if iteration % 20 == 0:
            await self.distribute_workers()
        
        supplyRatio = self.supply_used /(self.supply_used + self.supply_left);
        
        if (
            #Caso o supply esteja acabando e a gente tenha bases de controle
            #E a gente pode comprar um novo depósito e não tem nenhum depósito sendo construído
            supplyRatio > 0.8 and self.townhalls
            and self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.already_pending(UnitTypeId.SUPPLYDEPOT) < 1
        ):
            workers: Units = self.workers.gathering
            # If workers were found
            if workers:
                worker: Unit = workers.furthest_to(workers.center)
                location: Point2 = await self.find_placement(UnitTypeId.SUPPLYDEPOT, worker.position, placement_step=3)
                # If a placement location was found
                if location:
                    # Order worker to build exactly on that location
                    worker.build(UnitTypeId.SUPPLYDEPOT, location)
        
        #Constrói barracks(quartel general)
        #Seria bom a gente entender um pouco melhor as requisições das validações que ele faz pra garantir
        #um bom funcionamento do bot
        barracks_tech_requirement: float = self.tech_requirement_progress(UnitTypeId.BARRACKS)
        if (
            barracks_tech_requirement == 1 and
            self.structures(UnitTypeId.BARRACKS).ready.amount + self.already_pending(UnitTypeId.BARRACKS) < 4 and
            self.can_afford(UnitTypeId.BARRACKS)
        ):
            workers: Units = self.workers.gathering
            if (
                workers and self.townhalls
            ):  # need to check if townhalls.amount > 0 because placement is based on townhall location
                worker: Unit = workers.furthest_to(workers.center)
                # I chose placement_step 4 here so there will be gaps between barracks hopefully
                location: Point2 = await self.find_placement(
                    UnitTypeId.BARRACKS, self.townhalls.random.position, placement_step=4
                )
                if location:
                    worker.build(UnitTypeId.BARRACKS, location)
    
        if (
            self.can_afford(UnitTypeId.SCV) and self.supply_left > 0 and #Caso a gente possa criar SCVs
            (self.townhalls(UnitTypeId.COMMANDCENTER).idle or #Caso a gente tenha alguma "base" ociosa
             self.townhalls(UnitTypeId.ORBITALCOMMAND).idle)
        ):
            for th in self.townhalls.idle:
                th.train(UnitTypeId.SCV) #Pegue a base ociosa e crie um trabalhador

        #treinando marines
        for rax in self.structures(UnitTypeId.BARRACKS).ready.idle:
            if self.can_afford(UnitTypeId.MARINE):
                rax.train(UnitTypeId.MARINE)

        #mandando marines para o ataque
        marines: Units = self.units(UnitTypeId.MARINE).idle
        if marines.amount > 15:
            target: Point2 = self.enemy_structures.random_or(self.enemy_start_locations[0]).position
            for marine in marines:
                marine.attack(target)


        if iteration % 100 == 0:
            #Esse print a gente pode usar pra printar os parâmetros pra entender melhor oq eles retornam e como
            #as coisas funcionam no geral
            print("Supply used/left: ", self.supply_used, " ", self.supply_left)
            print("SELFStructures ", self.structures)
        


def main():
    run_game(
        maps.get("AcropolisLE"),
        [Bot(Race.Terran, unidosDaEc()), Computer(Race.Zerg, Difficulty.Easy)],
        realtime=False,
    )

if __name__ == "__main__":
    main()