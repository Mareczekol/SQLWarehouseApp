from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# app.debug = True #for error checking


class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    balance = db.Column(db.Float, default=0.0)


class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), unique=True)
    price = db.Column(db.Float)
    quantity = db.Column(db.Integer)


class Action(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.String(20))
    product_name = db.Column(db.String(100))
    price = db.Column(db.Float)
    quantity = db.Column(db.Integer)


@app.errorhandler(500)
def internal_server_error(error):
    # Log the error or display a user-friendly error page
    return "Internal Server Error", 500


@app.route('/', endpoint='home')
def home():
    account = load_account()
    inventory = load_inventory()
    return render_template('home.html', account=account, inventory=inventory)


@app.route('/purchase', methods=['POST'])
def purchase():
    product_name = request.form.get('product_name')
    price = request.form.get('price')
    quantity = request.form.get('quantity')

    if not product_name or not price or not quantity:
        return "Please fill all the fields", 400

    price = float(price)
    quantity = int(quantity)

    inventory = Inventory.query.filter_by(product_name=product_name).first()
    if inventory:
        inventory.quantity += quantity
    else:
        inventory = Inventory(product_name=product_name, price=price,
                              quantity=quantity)
        db.session.add(inventory)

    account = Account.query.first()
    account.balance -= price * quantity

    action = Action(action_type="purchase", product_name=product_name,
                    price=price, quantity=quantity)
    db.session.add(action)

    db.session.commit()

    return redirect(url_for('home'))


@app.route('/sale', methods=['POST'])
def sale():
    product_name = request.form.get('product_name')
    quantity = request.form.get('quantity')

    if not product_name or not quantity:
        return "Please fill all the fields", 400

    quantity = int(quantity)

    inventory = load_inventory()
    if product_name in inventory and inventory[product_name][1] >= quantity:
        inventory[product_name][1] -= quantity
        price = inventory[product_name][0]
        account = load_account()
        account += price * quantity

        action = ("sale", product_name, price, quantity)
        save_action(action)

        save_account(account)
        save_inventory(inventory)

    return redirect(url_for('home'))


@app.route('/change_balance', methods=['POST'])
def change_balance():
    amount = request.form.get('amount')

    if not amount:
        return "Please fill all the fields", 400

    amount = float(amount)

    account = load_account()
    account += amount

    action = ("change_balance", "", amount, 0)
    # Add empty strings for product_name and quantity
    save_action(action)

    save_account(account)

    return redirect(url_for('home'))


@app.route('/history', methods=['GET', 'POST'])
def history():
    actions = load_actions()
    start = request.args.get('start')
    end = request.args.get('end')

    if start and end:
        try:
            start = int(start)
            end = int(end)
            actions = actions[start:end]
        except (ValueError, IndexError):
            start = None
            end = None

    return render_template('history.html', actions=actions, start=start,
                           end=end)


def load_account():
    account = Account.query.first()
    if not account:
        account = Account(balance=0.0)
        db.session.add(account)
        db.session.commit()
    return account.balance


def save_account(account):
    account_obj = Account.query.first()
    if not account_obj:
        account_obj = Account(balance=account)
        db.session.add(account_obj)
    else:
        account_obj.balance = account
    db.session.commit()


def load_inventory():
    inventory = {}
    inventory_objs = Inventory.query.all()
    for item in inventory_objs:
        inventory[item.product_name] = [item.price, item.quantity]
    return inventory


def save_inventory(inventory):
    for product, details in inventory.items():
        inventory_obj = Inventory.query.filter_by(product_name=product).first()
        if inventory_obj:
            inventory_obj.price = details[0]
            inventory_obj.quantity = details[1]
        else:
            inventory_obj = Inventory(product_name=product, price=details[0],
                                      quantity=details[1])
            db.session.add(inventory_obj)
    db.session.commit()


def load_actions():
    actions = []
    action_objs = Action.query.all()
    for action in action_objs:
        actions.append((action.action_type, action.product_name, action.price,
                        action.quantity))
    return actions


def save_action(action):
    action_obj = Action(action_type=action[0], product_name=action[1],
                        price=action[2], quantity=action[3])
    db.session.add(action_obj)
    db.session.commit()


def check_data_integrity():
    account = Account.query.first()
    inventory = Inventory.query.all()
    actions = Action.query.all()

    file_account = load_account()
    file_inventory = load_inventory()
    file_actions = load_actions()

    if account.balance != file_account:
        print("Error: Account balance mismatch")

    for item in inventory:
        if item.product_name not in file_inventory or item.price != \
                file_inventory[item.product_name][0] or item.quantity \
                != file_inventory[item.product_name][1]:
            print(f"Error: Inventory mismatch for product {item.product_name}")

    if len(actions) != len(file_actions):
        print("Error: Actions count mismatch")
    else:
        for action, file_action in zip(actions, file_actions):
            if action.action_type != file_action[0] or action.product_name != \
                    file_action[1] or action.price != file_action[2] or \
                    action.quantity != file_action[3]:
                print(f"Error: Action mismatch for action {action.id}")


def create_tables():
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    create_tables()
    app.run()
