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
        defendersNumber = 10
        attackersNumber = 20
        targetEnemy: Point2 = self.enemy_structures.random_or(self.enemy_start_locations[0]).position
        targetDefender: Point2 = self.start_location.position
        if iteration % 20 == 0:
            await self.distribute_workers()
        
        supplyRatio = self.supply_used /(self.supply_used + self.supply_left);
        print( "Supply: ", self.supply_left)
        print("self.townhalls", self.townhalls.amount)
        if (
            #Caso o supply esteja acabando e a gente tenha bases de controle
            #E a gente pode comprar um novo depósito e não tem nenhum depósito sendo construído
            supplyRatio > 0.8 and self.townhalls
            and self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.already_pending(UnitTypeId.SUPPLYDEPOT) < 2 #Hiago: Modificado pra até 2 depósitos sendo criados
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
                    
        if self.gas_buildings.amount < 2 and self.can_afford(UnitTypeId.REFINERY):
            # All the vespene geysirs nearby, including ones with a refinery on top of it
            vgs = self.vespene_geyser.closer_than(10, self.townhalls(UnitTypeId.COMMANDCENTER).first)
            for vg in vgs:
                if self.gas_buildings.filter(lambda unit: unit.distance_to(vg) < 1):
                    continue
                # Select a worker closest to the vespene geysir
                worker: Unit = self.select_build_worker(vg)
                # Worker can be none in cases where all workers are dead
                # or 'select_build_worker' function only selects from workers which carry no minerals
                if worker is None:
                    continue
                # Issue the build command to the worker, important: vg has to be a Unit, not a position
                worker.build_gas(vg)
                # Only issue one build geysir command per frame
                break
    
        if (
            self.can_afford(UnitTypeId.SCV) and self.supply_left > 0 and #Caso a gente possa criar SCVs
            (self.townhalls(UnitTypeId.COMMANDCENTER).idle or #Caso a gente tenha alguma "base" ociosa
             self.townhalls(UnitTypeId.ORBITALCOMMAND).idle)
        ):
            for th in self.townhalls.idle:
                if(th.surplus_harvesters < 2):
                    th.train(UnitTypeId.SCV) #Pegue a base ociosa e crie um trabalhador
        
        # Se temos barracks
        if self.structures(UnitTypeId.BARRACKS).ready.exists:
            # Esses barracks estão construidos
            for lab in self.structures(UnitTypeId.BARRACKS).ready:
                # Me veja quais habilidades ele tem disponível
                abilities = await self.get_available_abilities(lab)
                # Se eu puder fazer um reator e tiver recursos
                if AbilityId.BUILD_REACTOR_BARRACKS in abilities and \
                self.can_afford(AbilityId.BUILD_REACTOR_BARRACKS):
                    # Faça um reator
                    self.do(lab(AbilityId.BUILD_REACTOR_BARRACKS))
            
        #treinando marines
        for rax in self.structures(UnitTypeId.BARRACKS).ready:
            if self.can_afford(UnitTypeId.MARINE) and len(rax.orders) < 2: # 2 ao mesmo tempo, por conta dos reatores
                rax.train(UnitTypeId.MARINE)
        
        marines: Units = self.units(UnitTypeId.MARINE).idle
        #Iremos sempre manter uma quantidade de defensores na base defendersNumber
        #Alem desses defensores, caso a quantidade restante seja maior que a quantidade minima de atacantes (attackersNumber) mandamos eles para o ataque
        cnt = 0 
        attack = True if marines.amount - defendersNumber > attackersNumber else False 
        for marine in marines:
            if cnt < defendersNumber:
                marine.attack(targetDefender)
            elif attack:                
                marine.attack(targetEnemy)
            cnt+=1


        if iteration % 100 == 0:
            #Esse print a gente pode usar pra printar os parâmetros pra entender melhor oq eles retornam e como
            #as coisas funcionam no geral
            print("Supply used/left: ", self.supply_used, " ", self.supply_left)
            print("SELFStructures ", self.structures)
        


def main():
    run_game(
        maps.get("AcropolisLE"),
        [Bot(Race.Terran, unidosDaEc()), Computer(Race.Zerg, Difficulty.MediumHard)],
        realtime=False,
    )

if __name__ == "__main__":
    main()