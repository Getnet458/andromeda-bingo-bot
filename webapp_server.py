# webapp_server.py - Complete working version

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import random
import time
import threading
from datetime import datetime
from collections import defaultdict

app = Flask(__name__, static_folder='webapp')
CORS(app)

# ========== DATA STORAGE ==========
users = defaultdict(lambda: {
    'balance': 100.0,
    'total_wagered': 0,
    'total_won': 0,
    'games_played': 0,
    'games_won': 0
})

owner_data = {
    'balance': 0.0,
    'total_commission_earned': 0.0,
    'total_games_hosted': 0,
    'total_prize_pool': 0.0
}

COMMISSION_RATE = 0.20
MAX_CARTELAS_PER_PLAYER = 10
active_games = {}
last_daily_claim = {}

# ========== HELPER FUNCTIONS ==========

def generate_cartela_number(existing):
    for num in range(1, 1001):
        if num not in existing:
            return num
    return random.randint(1001, 2000)

def generate_bingo_card():
    rows = []
    for i in range(5):
        start = i * 15 + 1
        end = (i + 1) * 15
        col = random.sample(range(start, end + 1), 5)
        rows.append(col)
    card = [[rows[j][i] for j in range(5)] for i in range(5)]
    card[2][2] = '★'
    return card

def check_bingo(marked):
    for i in range(5):
        if all(marked[i][j] for j in range(5)):
            return f"Row {i+1}"
    for j in range(5):
        if all(marked[i][j] for i in range(5)):
            return f"Column {j+1}"
    if all(marked[i][i] for i in range(5)):
        return "Main Diagonal"
    if all(marked[i][4-i] for i in range(5)):
        return "Secondary Diagonal"
    return None

def reset_game_room(stake):
    game_id = f"game_{stake}"
    active_games[game_id] = {
        'game_id': game_id, 'stake': stake, 'status': 'waiting',
        'players': 0, 'prize_pool': 0, 'drawn_numbers': [],
        'players_data': {}, 'game_number': random.randint(1, 100),
        'created_at': datetime.now().isoformat()
    }
    
    def countdown():
        time.sleep(30)
        if game_id in active_games and active_games[game_id]['status'] == 'waiting':
            active_games[game_id]['status'] = 'active'
            start_game_draws(game_id)
            print(f"🎮 Game {stake} ETB started!")
    
    threading.Thread(target=countdown, daemon=True).start()

def start_game_draws(game_id):
    def draw():
        game = active_games[game_id]
        numbers = list(range(1, 76))
        random.shuffle(numbers)
        
        for number in numbers:
            if game_id not in active_games or game['status'] != 'active':
                break
            
            game['drawn_numbers'].append(number)
            winners = []
            
            for uid, player in game['players_data'].items():
                if player.get('has_won'):
                    continue
                for i in range(5):
                    for j in range(5):
                        if player['card'][i][j] == number:
                            player['marked'][i][j] = True
                if check_bingo(player['marked']):
                    winners.append((uid, player))
            
            if winners:
                for uid, player in winners:
                    total = game['prize_pool']
                    winnings = total * 0.80
                    commission = total * 0.20
                    
                    owner_data['balance'] += commission
                    owner_data['total_commission_earned'] += commission
                    owner_data['total_prize_pool'] += total
                    owner_data['total_games_hosted'] += 1
                    
                    users[uid]['balance'] += winnings
                    users[uid]['total_won'] += winnings
                    users[uid]['games_won'] += 1
                    
                    player['has_won'] = True
                    game['winner'] = {'username': player['username'], 'amount': winnings}
                
                game['status'] = 'finished'
                print(f"🎉 Winner! Game {game_id} finished")
                
                time.sleep(30)
                reset_game_room(int(game_id.split('_')[1]))
                break
            
            time.sleep(random.uniform(2.5, 3.5))
    
    threading.Thread(target=draw, daemon=True).start()

# ========== API ENDPOINTS ==========

@app.route('/')
def index():
    return send_from_directory('webapp', 'index.html')

@app.route('/api/rooms', methods=['POST'])
def get_rooms():
    try:
        data = request.json
        uid = data.get('user_id')
        rooms = []
        
        for stake in [10, 20, 50]:
            gid = f"game_{stake}"
            if gid not in active_games:
                reset_game_room(stake)
            
            game = active_games[gid]
            if game['status'] == 'waiting':
                created = datetime.fromisoformat(game['created_at'])
                remaining = max(0, 30 - (datetime.now() - created).total_seconds())
                status = f"{int(remaining)}s"
            elif game['status'] == 'active':
                status = "4s"
            else:
                status = "Finished"
            
            rooms.append({
                'stake': stake,
                'status': status,
                'players': game['players'],
                'prize_pool': f"{game['prize_pool']:,}"
            })
        
        return jsonify({'rooms': rooms, 'balance': users[uid]['balance']})
    except Exception as e:
        print(f"Error in /api/rooms: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/balance', methods=['POST'])
def get_balance():
    try:
        data = request.json
        uid = data.get('user_id')
        return jsonify(dict(users[uid]))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/available_cartelas', methods=['POST'])
def get_available():
    try:
        data = request.json
        stake = data.get('stake')
        gid = f"game_{stake}"
        if gid not in active_games:
            return jsonify({'available_numbers': []})
        taken = [p['cartela_number'] for p in active_games[gid]['players_data'].values()]
        return jsonify({'available_numbers': taken})
    except Exception as e:
        return jsonify({'available_numbers': []})

@app.route('/api/join', methods=['POST'])
def join():
    try:
        data = request.json
        uid = str(data.get('user_id'))
        stake = data.get('stake')
        username = data.get('username', 'Player')
        requested = data.get('cartela_number')
        quantity = data.get('quantity', 1)
        
        gid = f"game_{stake}"
        if gid not in active_games:
            reset_game_room(stake)
        
        game = active_games[gid]
        
        if game['status'] == 'finished':
            return jsonify({'error': 'Game finished! New game soon...'}), 400
        
        # Check if already in game
        existing = [p for p in game['players_data'].values() if p['user_id'] == uid]
        if existing:
            return jsonify({
                'game': {
                    'game_id': gid,
                    'stake': stake,
                    'game_number': game['game_number'],
                    'balance': users[uid]['balance'],
                    'drawn_numbers': game['drawn_numbers'],
                    'prize_pool': game['prize_pool']
                },
                'cartelas': [{
                    'cartela_number': c['cartela_number'],
                    'card': c['card'],
                    'marked': c['marked']
                } for c in existing]
            })
        
        total_cost = stake * quantity
        
        if users[uid]['balance'] < total_cost:
            return jsonify({'error': f'Insufficient balance! Need {total_cost} ETB'}), 400
        
        # Deduct balance
        users[uid]['balance'] -= total_cost
        users[uid]['total_wagered'] += total_cost
        users[uid]['games_played'] += 1
        
        # Generate cartelas
        new_cartelas = []
        existing_numbers = [p['cartela_number'] for p in game['players_data'].values()]
        
        for i in range(quantity):
            if requested and i == 0 and requested not in existing_numbers:
                cartela_num = requested
            else:
                cartela_num = generate_cartela_number(existing_numbers + [c['cartela_number'] for c in new_cartelas])
            
            card = generate_bingo_card()
            marked = [[False]*5 for _ in range(5)]
            marked[2][2] = True
            
            cartela = {
                'cartela_id': f"{uid}_{cartela_num}",
                'user_id': uid,
                'username': username,
                'cartela_number': cartela_num,
                'card': card,
                'marked': marked,
                'has_won': False
            }
            
            game['players_data'][cartela['cartela_id']] = cartela
            new_cartelas.append(cartela)
            existing_numbers.append(cartela_num)
            game['prize_pool'] += stake
        
        game['players'] = len(set(p['user_id'] for p in game['players_data'].values()))
        
        print(f"✅ {username} bought {quantity} cartela(s) for {stake} ETB")
        
        return jsonify({
            'game': {
                'game_id': gid,
                'stake': stake,
                'game_number': game['game_number'],
                'balance': users[uid]['balance'],
                'drawn_numbers': game['drawn_numbers'],
                'prize_pool': game['prize_pool']
            },
            'cartelas': [{
                'cartela_number': c['cartela_number'],
                'card': c['card'],
                'marked': c['marked']
            } for c in new_cartelas]
        })
    except Exception as e:
        print(f"Error in /api/join: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/game_status', methods=['POST'])
def game_status():
    try:
        data = request.json
        uid = str(data.get('user_id'))
        gid = data.get('game_id')
        
        if gid not in active_games:
            return jsonify({'game_completed': True})
        
        game = active_games[gid]
        
        player_cartelas = [p for p in game['players_data'].values() if p['user_id'] == uid]
        if not player_cartelas:
            return jsonify({'game_completed': True})
        
        if game.get('winner'):
            player_won = any(c.get('has_won') for c in player_cartelas)
            win_amount = next((c.get('win_amount', 0) for c in player_cartelas if c.get('has_won')), 0)
            return jsonify({
                'game_completed': True,
                'won': player_won,
                'win_amount': win_amount,
                'winner_info': game['winner']
            })
        
        return jsonify({
            'game': {
                'game_id': gid,
                'stake': game['stake'],
                'game_number': game['game_number'],
                'balance': users[uid]['balance'],
                'drawn_numbers': game['drawn_numbers'],
                'prize_pool': game['prize_pool'],
                'status': game['status']
            },
            'cartelas': [{
                'cartela_number': c['cartela_number'],
                'card': c['card'],
                'marked': c['marked']
            } for c in player_cartelas]
        })
    except Exception as e:
        return jsonify({'game_completed': True, 'error': str(e)})

@app.route('/api/owner_balance', methods=['GET'])
def owner_balance():
    return jsonify({
        'owner_balance': owner_data['balance'],
        'total_commission_earned': owner_data['total_commission_earned'],
        'total_games_hosted': owner_data['total_games_hosted'],
        'total_prize_pool': owner_data['total_prize_pool'],
        'commission_rate': COMMISSION_RATE * 100
    })

@app.route('/api/daily_bonus', methods=['POST'])
def daily_bonus():
    try:
        data = request.json
        uid = data.get('user_id')
        
        today = datetime.now().date()
        last_claim = last_daily_claim.get(uid)
        
        if last_claim and last_claim >= today:
            return jsonify({'success': False, 'message': 'Already claimed today! Come back tomorrow.'})
        
        bonus = 50
        users[uid]['balance'] += bonus
        users[uid]['total_won'] += bonus
        last_daily_claim[uid] = today
        
        return jsonify({'success': True, 'bonus': bonus, 'new_balance': users[uid]['balance'], 'message': f'🎁 You received {bonus} ETB daily bonus!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    print("=" * 50)
    print("🎮 ANDROMEDA BINGO SERVER")
    print("=" * 50)
    print("📍 http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)