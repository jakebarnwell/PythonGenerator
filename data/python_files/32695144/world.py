
import pygame
import gameEngine
import config
import math
import hud
import random
import world

from pygame.locals import *

pygame.mixer.init()

clock = None

keysDown = []
ships = []
ammos = []
removables = set()
explosions = []
explosion_sound = pygame.mixer.Sound("sound/Blast-SoundBible.com-2068539061.ogg")
fire1_sound = pygame.mixer.Sound("sound/fire1.ogg")
fire2_sound = pygame.mixer.Sound("sound/fire2.ogg")

count = 0

player = None
screen = None

#bg_surface = pygame.image.load("graphics/pleiades.jpg")

bg_surface = pygame.Surface( config.resolution )
ship_surface = pygame.image.load("graphics/s1.png")

def writeHStoFile(score):
    f = open("hiscore.txt", "w")
    f.write( str(score) )
    return

def readHSfromFile():
    f = open("hiscore.txt", "r")
    score = f.readline()
    
    if ( int(score)):
        return score
    else:
        return 0
    


def startGame(screen):
    
    world.cleanup()
    
    world.screen = screen
    world.player = world.addShip( (0,0) )
    
    ships.append(world.player)

    for i in range(1,2):
        x = 300* random.random()
        y = x = 300* random.random()
        ships.append( addShip( (x,y) ) )
    
    print world.ships
    
    world.clock = pygame.time.Clock()    
    world.run()
    print count
    
    if(count > readHSfromFile() ):
        writeHStoFile(count)
    
    world.cleanup()
    pass

def cleanup():
    keysDown = []
    ships = []
    ammos = []
    removables = set()

    player = None
    screen = None
    mixer = None
    count = 0
    return
    

def update():
    
    for ship in ships:
        if (ship.update() == False ):
            removables.add(ship)
            ships.remove(ship)
            if(player._settings["target"] == ship):
               player._settings["target"] = None
               
        else:
            if(ship != player):
                temp = ship._ai.update()
                if(temp != None):
                    ammos.append(temp)
                    fire2_sound.play()
            ship.generateShield()
            ship.generateEnergy()
        
    for ammo in ammos:
        if (ammo.update() == False ):
            removables.add(ammo)
            ammos.remove(ammo)
            
    for explosion in explosions:
        if(explosion.update() == False):
            explosions.remove(explosion)
        
    return


def collide():
    
    temp_s = set()
    temp_a = set()
    
    
    for ammo in ammos:
        for ship in ships:
            if (gameEngine.checkCollision(ammo, ship) == True):
                #gameEngine.collide(ammo, ship)
                
                if ( ammo.collide() == False):
                    temp_a.add(ammo)
                if ( ship.collide() == False):
                    temp_s.add(ship)
        
        pass
    
        
    
    for i in temp_a:
        ammos.remove(i)
        removables.add(i)
		
        if(explosion_sound != None):
            explosion_sound.play()
    
    for i in temp_s:
        ships.remove(i)
        removables.add(i)
        if(i== player):
            return "GameOver"
        else:
            world.count += 1
        
    if(len(ships) == 1):
        return "SpawnMore"
    
    return ""

def drawAndClearRemovables():
    xx = config.playerRadiusFromCenter *math.cos( player.shipAngle() + math.radians(180) )
    yy = config.playerRadiusFromCenter *math.sin( player.shipAngle() + math.radians(180) )
    
    for r in removables:
        #t?h?n ??net, piirrot yms...
        pygame.draw.circle(screen, (255,255,0), r.getRelativeLocation( player.xy(), ((config.resolution[0] / 2 )+xx,(config.resolution[1] / 2 )+yy) ) , r.radius() + 10, 0)
        pass
    removables.clear()

def run():
    
    done = False
    
    while(not done):
        clock.tick(config.fps)
        
        world.update()
        temp = world.collide()
        
        if(temp == "SpawnMore" ):
            x = 5000 * random.random() - 2500
            y = 5000* random.random() - 2500
            ships.append( addShip( (x,y) ) )
        elif(temp == "GameOver" ):
            done = True
        
        world.drawBG(( -(bg_surface.get_width() / 2.0) -player.x() / 5.00  , -(bg_surface.get_height() / 2.0) -player.y() / 5.00  ))
        world.drawAndClearRemovables()
        world.drawObjects()
        
        world.drawHUD()
        
        
        removables.clear()
        
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                keysDown.append(event.key)
            elif event.type == KEYUP:
                if event.key in keysDown:
                    keysDown.remove(event.key)
            elif event.type == QUIT:
                done = True

        for key in keysDown:
            if (action(player, key, done) == True):
                done = True
        
        pass
    
    
    pass
    

def action(player, key, done):
    if (key == K_UP):
        player.thrust()
    elif (key == K_DOWN):
        player.speedDown()
    elif (key == K_LEFT):
        player.decreaseAngle()
    elif (key == K_RIGHT):
        player.increaseAngle()
    elif (key == K_SPACE):
        if(player.depleteEnergy(3) == True):
            ammos.append(player.shoot())
            fire1_sound.play()
    elif (key == K_t):
        player._ai.setTarget()
            
    elif (key == K_ESCAPE):
        return True
    
    return False


def addShip( xy ):
    data = { "acceleration": 0.001,
            "currentAngle": 0,
            "newAngle": 0,
            "x": xy[0],
            "y": xy[1],
            "turningSpeed": math.radians(135),
            "currentSpeed": 0,
            "maxSpeed": 10,
            "radius": 10,
            "mass":	10,
            "engineForce": 100,
            "ttl": -1,
            "all_objects": ships,
            "ai_target": "none",
            "target": None,
            "distance_to_target": 2**31,
            "ai_actions": None,
            "angle_to_target": 0}
    
    return gameEngine.Ship(data, ships)
    

def drawBG( location ):
    pygame.display.flip()
    world.screen.fill( (0,0,0) )
    world.screen.blit( bg_surface, location )
    
def drawHUD():
    xx = config.playerRadiusFromCenter *math.cos( player.shipAngle() + math.radians(180) )
    yy = config.playerRadiusFromCenter *math.sin( player.shipAngle() + math.radians(180) )
    
    hud.drawStats(screen, player, player._settings["target"])
    
    if(player._settings["target"] != None):
        hud.drawLines(screen, player.getRelativeLocation( player.xy(), ((config.resolution[0] / 2 )+xx,(config.resolution[1] / 2 )+yy)), player.shipAngle() , player._settings["target"].getRelativeLocation(player.xy()) )
    else:
        hud.drawLines(screen, player.getRelativeLocation( player.xy(), ((config.resolution[0] / 2 )+xx,(config.resolution[1] / 2 )+yy)), player.shipAngle() , None )
    
    hud.drawSpeedLine(screen, player)


def drawObjects():
    xx = config.playerRadiusFromCenter *math.cos( player.shipAngle() + math.radians(180) )
    yy = config.playerRadiusFromCenter *math.sin( player.shipAngle() + math.radians(180) )
    
    for ship in ships:
        temp_s = ship_surface.copy()
        zoom = 3* float(ship.radius()) / float(temp_s.get_height())
        temp_s = pygame.transform.rotozoom (temp_s, -math.degrees(ship.shipAngle())-90, zoom)
        pygame.draw.circle(screen, (0,255,0), ship.getRelativeLocation( player.xy(), ( (config.resolution[0]/2) +xx, (config.resolution[1] / 2 ) +yy) ) , ship.radius(), 0)
        world.screen.blit(temp_s, ship.getRelativeLocation( player.xy(), ((config.resolution[0] / 2 )+xx -(temp_s.get_width() / 2) ,(config.resolution[1] / 2 )+yy -(temp_s.get_height() / 2) ) ))
        pass
    
    for ammo in ammos:
        pygame.draw.circle(screen, (0,255,0), ammo.getRelativeLocation( player.xy(), ((config.resolution[0] / 2 )+xx, (config.resolution[1] / 2 )+yy) ) , ammo.radius(), 0)
        pass
    
    for r in removables:
        pygame.draw.circle(screen, (0,0,255), r.getRelativeLocation( player.xy(), ((config.resolution[0] / 2 )+xx,(config.resolution[1] / 2 )+yy) ) , r.radius(), 0)
        pass
    
    return
    
