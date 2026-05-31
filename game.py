import http.server
import socketserver
import threading
import webbrowser
import time

# --- Game HTML, CSS and JavaScript Code ---
game_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, orientation=landscape">
    <title>Mega Maze - Landscape Action Mod</title>
    <style>
        body {
            margin: 0; padding: 0;
            background: #090d16;
            color: white; font-family: 'Segoe UI', Arial, sans-serif;
            overflow: hidden; user-select: none;
            touch-action: none;
        }
        #ui-layer {
            position: absolute; top: 12px; left: 15px; right: 15px;
            display: flex; justify-content: space-between; align-items: center;
            font-size: 14px; font-weight: bold; z-index: 10;
            pointer-events: none;
        }
        .hud-box {
            background: rgba(9, 13, 22, 0.9);
            padding: 8px 16px; border-radius: 12px;
            border: 2px solid rgba(59, 130, 246, 0.3);
            box-shadow: 0 4px 15px rgba(0,0,0,0.6);
            display: flex; align-items: center; gap: 8px;
        }
        canvas { display: block; width: 100vw; height: 100vh; }
        
        /* Controls Optimized for Landscape Mode */
        #controls {
            position: absolute; bottom: 20px; left: 0; width: 100%;
            display: flex; justify-content: space-between; align-items: flex-end;
            padding: 0 40px; box-sizing: border-box; pointer-events: none;
            z-index: 10;
        }
        #joystick-zone {
            width: 100px; height: 100px;
            background: rgba(255, 255, 255, 0.08);
            border: 2px solid rgba(255, 255, 255, 0.25);
            border-radius: 50%; position: relative; pointer-events: auto;
        }
        #joystick-stick {
            width: 40px; height: 40px; background: #ff4757;
            border-radius: 50%; position: absolute; top: 28px; left: 28px;
            box-shadow: 0 5px 12px rgba(0,0,0,0.6);
            display: flex; justify-content: center; align-items: center;
            font-size: 9px; font-weight: bold; color: white;
        }
        .btn-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
            pointer-events: auto;
        }
        .action-btn {
            width: 75px; height: 75px;
            border: none; border-radius: 50%; color: white;
            font-weight: bold; font-size: 13px; cursor: pointer;
            box-shadow: 0 6px 15px rgba(0,0,0,0.4);
            transition: 0.1s;
        }
        #shoot-btn {
            background: linear-gradient(135deg, #ef4444, #b91c1c);
            box-shadow: 0 6px 15px rgba(239, 68, 68, 0.4);
            opacity: 0.3;
        }
        #jump-btn {
            background: linear-gradient(135deg, #a855f7, #2563eb);
            box-shadow: 0 6px 15px rgba(37, 99, 235, 0.4);
        }
        #drop-btn {
            background: linear-gradient(135deg, #f59e0b, #d97706);
            box-shadow: 0 6px 15px rgba(245, 158, 11, 0.4);
        }
        .action-btn:active { transform: scale(0.90); }
        
        #status-screen {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(5, 7, 12, 0.96);
            display: none; flex-direction: column;
            justify-content: center; align-items: center; z-index: 20;
        }
        #status-screen h1 { font-size: 36px; margin-bottom: 5px; letter-spacing: 2px; }
        #status-screen p { font-size: 16px; margin-bottom: 20px; text-align: center; color: #94a3b8; }
        #restart-btn {
            padding: 12px 35px; font-size: 16px; font-weight: bold;
            background: #2563eb; border: none; border-radius: 50px;
            color: white; cursor: pointer; box-shadow: 0 5px 15px rgba(37,99,235,0.4);
        }
    </style>
</head>
<body>

    <div id="ui-layer">
        <div class="hud-box">Masti Score: <span id="score">0</span></div>
        <div class="hud-box" id="ammo-hud" style="color: #facc15; display: none;">🔫 AMMO: <span id="ammo-count">0</span></div>
        <div class="hud-box" id="key-status" style="color: #feca57;">🚨 MISSION: Find Big Gun 🔫 & Key 🔑</div>
    </div>
    
    <canvas id="gameCanvas"></canvas>

    <div id="controls">
        <div id="joystick-zone"><div id="joystick-stick">MOVE</div></div>
        <div class="btn-container">
            <button id="shoot-btn" class="action-btn">SHOOT 🔫</button>
            <button id="jump-btn" class="action-btn">JUMP</button>
            <button id="drop-btn" class="action-btn">DROP 🎒</button>
        </div>
    </div>

    <div id="status-screen">
        <h1 id="status-title">Game Over! 💀</h1>
        <p id="status-desc">Granny trapped you inside the mega maze.</p>
        <button id="restart-btn" onclick="resetGame()">Try Again</button>
    </div>

    <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const scoreEl = document.getElementById('score');
        const ammoHud = document.getElementById('ammo-hud');
        const ammoCountEl = document.getElementById('ammo-count');
        const keyStatusEl = document.getElementById('key-status');
        const statusScreen = document.getElementById('status-screen');
        const statusTitle = document.getElementById('status-title');
        const statusDesc = document.getElementById('status-desc');
        const shootBtn = document.getElementById('shoot-btn');
        const dropBtn = document.getElementById('drop-btn');

        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        let score = 0;
        let audioCtx = null;
        let isGameOver = false;
        let hasKey = false;
        let hasGun = false;
        let ammo = 0;
        let isPlayerSafe = false;

        let isGrannyDead = false;
        let grannyDeadTimer = 0;
        let grannyBaseSpeed = 2.0;

        const tileSize = 40; 
        let cols = Math.floor(canvas.width / tileSize);
        let rows = Math.floor(canvas.height / tileSize);

        let map = [];
        let safeZones = []; 
        let bullets = [];
        let ammoBoxes = []; 

        function generateComplexMaze() {
            cols = Math.floor(canvas.width / tileSize);
            rows = Math.floor(canvas.height / tileSize);
            map = [];
            for (let r = 0; r < rows; r++) {
                let rowArray = [];
                for (let c = 0; c < cols; c++) {
                    if (r === 0 || r === rows - 1 || c === 0 || c === cols - 1) {
                        rowArray.push(1);
                    } else {
                        if (
                            (r % 2 === 0 && c % 4 === 0) || 
                            (c % 3 === 0 && r % 3 === 0) ||
                            (r === 3 && c > 2 && c < cols - 4) ||
                            (c === 5 && r > 2 && r < rows - 3) ||
                            (r === rows - 4 && c > 4 && c < cols - 2) ||
                            (c === cols - 4 && r > 4 && r < rows - 2) ||
                            (r % 5 === 0 && c % 2 === 0)
                        ) {
                            rowArray.push(1);
                        } else {
                            rowArray.push(0);
                        }
                    }
                }
                map.push(rowArray);
            }

            for (let r = 2; r < rows - 2; r++) {
                for (let c = 2; c < cols - 2; c++) {
                    if (Math.random() < 0.25) map[r][c] = 0;
                }
            }

            map[1][1] = 0; map[1][2] = 0; map[2][1] = 0; 
            map[rows-2][2] = 0; map[rows-3][2] = 0;       
            map[rows-2][cols-2] = 2; 

            safeZones = [];
            while(safeZones.length < 2) {
                let rc = Math.floor(Math.random() * (cols - 4)) + 2;
                let rr = Math.floor(Math.random() * (rows - 4)) + 2;
                if(map[rr][rc] === 0 && !(rc === 1 && rr === 1)) {
                    if(!safeZones.some(z => z.r === rr && z.c === rc)) {
                        safeZones.push({ r: rr, c: rc, x: rc * tileSize, y: rr * tileSize });
                    }
                }
            }
        }
        generateComplexMaze();

        const player = { x: tileSize + tileSize/2, y: tileSize + tileSize/2, radius: 14, speed: 4.8, vx: 0, vy: 0, lastAngle: 0 };
        const enemy = { x: tileSize*2 + tileSize/2, y: (rows - 2) * tileSize + tileSize/2, radius: 16, speed: grannyBaseSpeed, lastAngle: 0 };
        
        let goldenKey = { x: 0, y: 0, collected: false };
        let gunItem = { x: 0, y: 0, collected: false };
        let notes = [];

        function placeItems() {
            let keyPlaced = false;
            while(!keyPlaced) {
                let rc = Math.floor(Math.random() * (cols - 4)) + 2;
                let rr = Math.floor(Math.random() * (rows - 4)) + 2;
                if(map[rr][rc] === 0 && rr > rows/2) { 
                    goldenKey.x = rc * tileSize + tileSize/2;
                    goldenKey.y = rr * tileSize + tileSize/2;
                    keyPlaced = true;
                }
            }

            let gunPlaced = false;
            while(!gunPlaced) {
                let rc = Math.floor(Math.random() * (cols - 4)) + 2;
                let rr = Math.floor(Math.random() * (rows - 4)) + 2;
                if(map[rr][rc] === 0 && rc > cols/3) { 
                    gunItem.x = rc * tileSize + tileSize/2;
                    gunItem.y = rr * tileSize + tileSize/2;
                    gunPlaced = true;
                }
            }

            ammoBoxes = [];
            while(ammoBoxes.length < 3) {
                let rc = Math.floor(Math.random() * (cols - 4)) + 2;
                let rr = Math.floor(Math.random() * (rows - 4)) + 2;
                if(map[rr][rc] === 0) {
                    ammoBoxes.push({ x: rc * tileSize + tileSize/2, y: rr * tileSize + tileSize/2, collected: false });
                }
            }

            notes = [];
            while(notes.length < 5) {
                let rc = Math.floor(Math.random() * (cols - 2)) + 1;
                let rr = Math.floor(Math.random() * (rows - 2)) + 1;
                if(map[rr][rc] === 0 && !(rc===1 && rr===1)) {
                    notes.push({ x: rc * tileSize + tileSize/2, y: rr * tileSize + tileSize/2, radius: 8 });
                }
            }
        }
        placeItems();

        function initAudio() {
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }

        function playTone(freq, type = 'sine', duration = 0.2) {
            initAudio(); if (!audioCtx) return;
            const osc = audioCtx.createOscillator(); const gain = audioCtx.createGain();
            osc.type = type; osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
            gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
            osc.connect(gain); gain.connect(audioCtx.destination);
            osc.start(); osc.stop(audioCtx.currentTime + duration);
        }

        function isColliding(x, y, radius) {
            let points = [{x: x-radius, y: y-radius}, {x: x+radius, y: y-radius}, {x: x-radius, y: y+radius}, {x: x+radius, y: y+radius}, {x: x, y: y}];
            for (let pt of points) {
                let c = Math.floor(pt.x / tileSize); let r = Math.floor(pt.y / tileSize);
                if (r >= 0 && r < rows && c >= 0 && c < cols) {
                    if (map[r][c] === 1) return true; 
                }
            }
            return false;
        }

        // --- Joystick Controls ---
        const stick = document.getElementById('joystick-stick');
        const zone = document.getElementById('joystick-zone');
        let joystickActive = false; let startX, startY;

        zone.addEventListener('touchstart', (e) => {
            if(isGameOver) return; initAudio(); joystickActive = true;
            startX = e.touches[0].clientX; startY = e.touches[0].clientY;
        });
        zone.addEventListener('touchmove', (e) => {
            if (!joystickActive || isGameOver) return;
            let dx = e.touches[0].clientX - startX; let dy = e.touches[0].clientY - startY;
            const dist = Math.min(Math.sqrt(dx*dx + dy*dy), 35);
            const angle = Math.atan2(dy, dx);
            stick.style.transform = `translate(${dist * Math.cos(angle)}px, ${dist * Math.sin(angle)}px)`;
            player.vx = (dist * Math.cos(angle) / 35) * player.speed;
            player.vy = (dist * Math.sin(angle) / 35) * player.speed;
        });
        zone.addEventListener('touchend', () => {
            joystickActive = false; stick.style.transform = 'translate(0px, 0px)';
            player.vx = 0; player.vy = 0;
        });

        // --- Keyboard Controls ---
        let keysPressed = {};
        window.addEventListener('keydown', (e) => { keysPressed[e.key] = true; initAudio(); });
        window.addEventListener('keyup', (e) => { keysPressed[e.key] = false; });

        function handleKeyboardInput() {
            if (joystickActive) return; 
            player.vx = 0; player.vy = 0;
            if (keysPressed['ArrowUp'] || keysPressed['w']) player.vy = -player.speed;
            if (keysPressed['ArrowDown'] || keysPressed['s']) player.vy = player.speed;
            if (keysPressed['ArrowLeft'] || keysPressed['a']) player.vx = -player.speed;
            if (keysPressed['ArrowRight'] || keysPressed['d']) player.vx = player.speed;
        }

        // --- Action Buttons Trigger ---
        document.getElementById('jump-btn').addEventListener('touchstart', (e) => {
            if(isGameOver) return; e.preventDefault(); triggerJump();
        });
        shootBtn.addEventListener('touchstart', (e) => {
            if(isGameOver) return; e.preventDefault(); triggerShoot();
        });
        dropBtn.addEventListener('touchstart', (e) => {
            if(isGameOver) return; e.preventDefault(); triggerDrop();
        });
        window.addEventListener('keydown', (e) => {
            if(e.key.toLowerCase() === 'x') triggerShoot();
            if(e.key === ' ' || e.key.toLowerCase() === 'z') triggerJump();
            if(e.key.toLowerCase() === 'q') triggerDrop(); 
        });

        function triggerJump() {
            playTone(600, 'triangle', 0.15);
            player.radius = 19; setTimeout(() => player.radius = 14, 120);
        }

        function triggerShoot() {
            if(!hasGun || ammo <= 0 || isGameOver) return;
            ammo--;
            ammoCountEl.innerText = ammo;
            playTone(150, 'sawtooth', 0.12); 
            bullets.push({
                x: player.x, y: player.y,
                vx: Math.cos(player.lastAngle) * 9, vy: Math.sin(player.lastAngle) * 9,
                radius: 4
            });
            if(ammo <= 0) shootBtn.style.opacity = "0.3";
        }

        // --- DROP ITEM LOGIC ---
        function triggerDrop() {
            if(isGameOver) return;
            
            if (hasKey) {
                hasKey = false;
                goldenKey.collected = false;
                goldenKey.x = player.x;
                goldenKey.y = player.y;
                playTone(300, 'triangle', 0.2);
                updateMissionStatus();
                return;
            } 
            
            if (hasGun) {
                hasGun = false;
                gunItem.collected = false;
                gunItem.x = player.x;
                gunItem.y = player.y;
                shootBtn.style.opacity = "0.3";
                ammoHud.style.display = "none";
                playTone(250, 'triangle', 0.2);
                updateMissionStatus();
                return;
            }
        }

        function updateMissionStatus() {
            if(!hasGun && !hasKey) {
                keyStatusEl.innerText = "🚨 MISSION: Find Big Gun 🔫 & Key 🔑";
                keyStatusEl.style.color = "#feca57";
            } else if(hasGun && !hasKey) {
                keyStatusEl.innerText = `🚨 MISSION: Only ${ammo} Bullets! Find Key 🔑`;
                keyStatusEl.style.color = "#feca57";
            } else if(!hasGun && hasKey) {
                keyStatusEl.innerText = "🔓 DOOR OPENED! Escape Fast! 🚪 (No Weapon!)";
                keyStatusEl.style.color = "#2ed573";
            } else if(hasGun && hasKey) {
                keyStatusEl.innerText = "🔓 DOOR OPENED! Escape Fast! 🚪";
                keyStatusEl.style.color = "#2ed573";
            }
        }

        function resetGame() {
            score = 0; scoreEl.innerText = score;
            hasKey = false; goldenKey.collected = false;
            hasGun = false; gunItem.collected = false; ammo = 0;
            shootBtn.style.opacity = "0.3"; ammoHud.style.display = "none";
            keyStatusEl.innerText = "🚨 MISSION: Find Big Gun 🔫 & Key 🔑"; keyStatusEl.style.color = "#feca57";
            player.x = tileSize + tileSize/2; player.y = tileSize + tileSize/2;
            player.vx = 0; player.vy = 0; player.lastAngle = 0;
            grannyBaseSpeed = 2.0; isGrannyDead = false;
            enemy.x = tileSize*2 + tileSize/2; enemy.y = (rows - 2) * tileSize + tileSize/2; enemy.speed = grannyBaseSpeed; enemy.lastAngle = 0;
            bullets = []; generateComplexMaze(); placeItems(); isGameOver = false; isPlayerSafe = false;
            statusScreen.style.display = 'none';
        }

        function drawEyes(ctx, centerX, centerY, radius, angle, isGranny) {
            ctx.save(); ctx.translate(centerX, centerY); ctx.rotate(angle);
            ctx.beginPath(); ctx.arc(radius * 0.35, -radius * 0.3, radius * 0.28, 0, Math.PI * 2);
            ctx.fillStyle = '#ffffff'; ctx.fill();
            ctx.beginPath(); ctx.arc(radius * 0.45, -radius * 0.3, radius * 0.12, 0, Math.PI * 2);
            ctx.fillStyle = isGranny ? '#ff0000' : '#000000'; ctx.fill();
            ctx.beginPath(); ctx.arc(radius * 0.35, radius * 0.3, radius * 0.28, 0, Math.PI * 2);
            ctx.fillStyle = '#ffffff'; ctx.fill();
            ctx.beginPath(); ctx.arc(radius * 0.45, radius * 0.3, radius * 0.12, 0, Math.PI * 2);
            ctx.fillStyle = isGranny ? '#ff0000' : '#000000'; ctx.fill();
            ctx.restore();
        }

        function update() {
            if (isGameOver) return;
            handleKeyboardInput();

            let nextX = player.x + player.vx;
            let nextY = player.y + player.vy;
            if (!isColliding(nextX, player.y, player.radius)) player.x = nextX;
            if (!isColliding(player.x, nextY, player.radius)) player.y = nextY;

            if (player.vx !== 0 || player.vy !== 0) player.lastAngle = Math.atan2(player.vy, player.vx);

            let pCellC = Math.floor(player.x / tileSize);
            let pCellR = Math.floor(player.y / tileSize);
            isPlayerSafe = safeZones.some(z => z.r === pCellR && z.c === pCellC);

            if (isGrannyDead) {
                if (Date.now() > grannyDeadTimer) {
                    isGrannyDead = false; 
                    enemy.x = tileSize*2 + tileSize/2; enemy.y = (rows - 2) * tileSize + tileSize/2;
                    grannyBaseSpeed += 0.4; 
                    enemy.speed = grannyBaseSpeed;
                }
            }

            if (!isGrannyDead) {
                let diffX = player.x - enemy.x; let diffY = player.y - enemy.y;
                let angle = Math.atan2(diffY, diffX);
                if (diffX !== 0 || diffY !== 0) enemy.lastAngle = angle;
                
                let stepX = Math.cos(angle) * enemy.speed; let stepY = Math.sin(angle) * enemy.speed;

                if (!isColliding(enemy.x + stepX, enemy.y, enemy.radius)) enemy.x += stepX;
                else if (!isColliding(enemy.x, enemy.y + (diffY > 0 ? enemy.speed : -enemy.speed), enemy.radius)) enemy.y += (diffY > 0 ? enemy.speed : -enemy.speed);
                
                if (!isColliding(enemy.x, enemy.y + stepY, enemy.radius)) enemy.y += stepY;
                else if (!isColliding(enemy.x + (diffX > 0 ? enemy.speed : -enemy.speed), enemy.y, enemy.radius)) enemy.x += (diffX > 0 ? enemy.speed : -enemy.speed);

                let distToEnemy = Math.sqrt((player.x - enemy.x)**2 + (player.y - enemy.y)**2);
                if (distToEnemy < player.radius + enemy.radius && !isPlayerSafe) {
                    isGameOver = true;
                    playTone(140, 'sawtooth', 0.8);
                    statusTitle.innerText = "Game Over! 💀";
                    statusDesc.innerText = "Granny caught you in the landscape maze!";
                    statusScreen.style.display = 'flex';
                }
            }

            for (let i = bullets.length - 1; i >= 0; i--) {
                bullets[i].x += bullets[i].vx; bullets[i].y += bullets[i].vy;
                if (isColliding(bullets[i].x, bullets[i].y, bullets[i].radius)) {
                    bullets.splice(i, 1); continue;
                }
                if (!isGrannyDead) {
                    let bDist = Math.sqrt((bullets[i].x - enemy.x)**2 + (bullets[i].y - enemy.y)**2);
                    if (bDist < bullets[i].radius + enemy.radius) {
                        isGrannyDead = true;
                        grannyDeadTimer = Date.now() + 10000; 
                        playTone(100, 'sine', 0.5);
                        bullets.splice(i, 1);
                        score += 30; scoreEl.innerText = score;
                        break;
                    }
                }
            }

            if (!gunItem.collected) {
                let distToGun = Math.sqrt((player.x - gunItem.x)**2 + (player.y - gunItem.y)**2);
                if (distToGun < player.radius + 15) {
                    hasGun = true; gunItem.collected = true;
                    if(ammo === 0) ammo = 2; 
                    ammoCountEl.innerText = ammo;
                    ammoHud.style.display = "flex";
                    shootBtn.style.opacity = "1";
                    playTone(450, 'sine', 0.3);
                    updateMissionStatus();
                }
            }

            for (let i = ammoBoxes.length - 1; i >= 0; i--) {
                if (!ammoBoxes[i].collected) {
                    let dist = Math.sqrt((player.x - ammoBoxes[i].x)**2 + (player.y - ammoBoxes[i].y)**2);
                    if (dist < player.radius + 12) {
                        ammoBoxes[i].collected = true;
                        if(hasGun) {
                            ammo += 1; 
                            ammoCountEl.innerText = ammo;
                            shootBtn.style.opacity = "1";
                            playTone(500, 'sine', 0.15);
                        }
                    }
                }
            }

            if (!goldenKey.collected) {
                let distToKey = Math.sqrt((player.x - goldenKey.x)**2 + (player.y - goldenKey.y)**2);
                if (distToKey < player.radius + 12) {
                    hasKey = true; goldenKey.collected = true;
                    playTone(650, 'sine', 0.4);
                    updateMissionStatus();
                }
            }

            if (hasKey) {
                let targetX = (cols - 2) * tileSize + tileSize/2; let targetY = (rows - 2) * tileSize + tileSize/2;
                if (Math.sqrt((player.x - targetX)**2 + (player.y - targetY)**2) < player.radius + 15) {
                    isGameOver = true; playTone(850, 'sine', 0.6);
                    statusTitle.innerText = "YOU ESCAPED! 🏆"; statusTitle.style.color = "#2ed573";
                    statusDesc.innerText = `Superb! You escaped the maze with ${score} points!`;
                    statusScreen.style.display = 'flex';
                }
            }

            for (let i = notes.length - 1; i >= 0; i--) {
                if (Math.sqrt((player.x - notes[i].x)**2 + (player.y - notes[i].y)**2) < player.radius + notes[i].radius) {
                    playTone(350, 'sine', 0.1); notes.splice(i, 1); score += 10; scoreEl.innerText = score;
                    let spawned = false;
                    while(!spawned) {
                        let rc = Math.floor(Math.random() * (cols - 2)) + 1; let rr = Math.floor(Math.random() * (rows - 2)) + 1;
                        if(map[rr][rc] === 0) {
                            notes.push({ x: rc * tileSize + tileSize/2, y: rr * tileSize + tileSize/2, radius: 8 });
                            spawned = true;
                        }
                    }
                }
            }
        }

        function render() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            for (let r = 0; r < rows; r++) {
                for (let c = 0; c < cols; c++) {
                    if (map[r][c] === 1 || (map[r][c] === 2 && !hasKey)) {
                        ctx.fillStyle = '#111827'; ctx.fillRect(c * tileSize, r * tileSize, tileSize, tileSize);
                        ctx.strokeStyle = '#1e40af'; ctx.lineWidth = 1; ctx.strokeRect(c * tileSize, r * tileSize, tileSize, tileSize);
                    }
                }
            }

            safeZones.forEach(zone => {
                ctx.fillStyle = 'rgba(34, 197, 94, 0.2)'; ctx.fillRect(zone.x, zone.y, tileSize, tileSize);
                ctx.strokeStyle = '#22c55e'; ctx.lineWidth = 2; ctx.strokeRect(zone.x + 2, zone.y + 2, tileSize - 4, tileSize - 4);
                ctx.fillStyle = '#22c55e'; ctx.font = 'bold 8px Arial'; ctx.fillText("SAFE", zone.x + 8, zone.y + 24);
            });

            if (hasKey) {
                let ex = (cols - 2) * tileSize; let ey = (rows - 2) * tileSize;
                ctx.fillStyle = '#78350f'; ctx.fillRect(ex + 4, ey, tileSize - 8, tileSize);
                ctx.strokeStyle = '#f59e0b'; ctx.lineWidth = 3; ctx.strokeRect(ex + 4, ey, tileSize - 8, tileSize);
                ctx.beginPath(); ctx.arc(ex + tileSize - 10, ey + tileSize/2, 3, 0, Math.PI * 2); ctx.fillStyle = '#fbbf24'; ctx.fill();
            }

            if (!gunItem.collected) {
                ctx.fillStyle = 'rgba(239, 68, 68, 0.2)';
                ctx.beginPath(); ctx.arc(gunItem.x, gunItem.y, 16, 0, Math.PI * 2); ctx.fill(); 
                ctx.fillStyle = '#fff'; ctx.font = '16px Arial'; ctx.fillText("🔫", gunItem.x - 9, gunItem.y + 6);
            }

            ammoBoxes.forEach(box => {
                if (!box.collected) {
                    ctx.fillStyle = '#fff'; ctx.font = '13px Arial';
                    ctx.fillText("🔋", box.x - 6, box.y + 5);
                }
            });

            if (!goldenKey.collected) {
                ctx.fillStyle = '#fff'; ctx.font = '12px Arial'; ctx.fillText("🔑", goldenKey.x - 6, goldenKey.y + 5);
            }

            notes.forEach(note => {
                ctx.beginPath(); ctx.arc(note.x, note.y, note.radius, 0, Math.PI * 2); ctx.fillStyle = '#ec4899'; ctx.fill(); 
            });

            bullets.forEach(b => {
                ctx.beginPath(); ctx.arc(b.x, b.y, b.radius, 0, Math.PI * 2); ctx.fillStyle = '#facc15'; ctx.fill();
            });
            
            ctx.beginPath(); ctx.arc(player.x, player.y, player.radius, 0, Math.PI * 2);
            ctx.fillStyle = isPlayerSafe ? '#22c55e' : '#f97316'; ctx.fill();
            ctx.lineWidth = 2; ctx.strokeStyle = '#ffffff'; ctx.stroke();
            drawEyes(ctx, player.x, player.y, player.radius, player.lastAngle, false);

            if (hasGun) {
                ctx.save(); ctx.translate(player.x, player.y); ctx.rotate(player.lastAngle);
                ctx.fillStyle = '#4b5563'; ctx.fillRect(11, -3, 14, 5); 
                ctx.restore();
            }

            if (!isGrannyDead) {
                ctx.beginPath(); ctx.arc(enemy.x, enemy.y, enemy.radius, 0, Math.PI * 2);
                ctx.fillStyle = grannyBaseSpeed > 2.0 ? '#b91c1c' : '#ef4444'; ctx.fill();
                ctx.lineWidth = 2; ctx.strokeStyle = '#7f1d1d'; ctx.stroke();
                drawEyes(ctx, enemy.x, enemy.y, enemy.radius, enemy.lastAngle, true);
                
                let angle = Math.atan2(player.y - enemy.y, player.x - enemy.x);
                ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 4; ctx.lineCap = 'round'; ctx.beginPath();
                ctx.moveTo(enemy.x + Math.cos(angle+0.4)*10, enemy.y + Math.sin(angle+0.4)*10);
                ctx.lineTo(enemy.x + Math.cos(angle+0.4)*32, enemy.y + Math.sin(angle+0.4)*32); ctx.stroke();
            } else {
                ctx.fillStyle = '#ef4444'; ctx.font = 'bold 10px Arial';
                let timeLeft = Math.ceil((grannyDeadTimer - Date.now()) / 1000);
                if(timeLeft > 0) ctx.fillText(`👵💀 ANGRY RESPAWN IN ${timeLeft}s`, enemy.x - 55, enemy.y);
            }
        }

        function loop() { update(); render(); requestAnimationFrame(loop); }
        loop();

        window.addEventListener('resize', () => {
            canvas.width = window.innerWidth; canvas.height = window.innerHeight;
            generateComplexMaze(); placeItems();
        });
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(game_html)

PORT = 8000
Handler = http.server.SimpleHTTPRequestHandler

def start_server():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Server is running on port: {PORT}")
        httpd.serve_forever()

server_thread = threading.Thread(target=start_server)
server_thread.daemon = True
server_thread.start()

time.sleep(1)
print("Launching Ultimate Landscape Action Maze Mod with Drop Item Support...")
webbrowser.open(f"http://localhost:{PORT}/index.html")

while True:
    time.sleep(1)
