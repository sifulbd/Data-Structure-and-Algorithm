# Imports necessary packages and libraries.
import mysql.connector
import csv
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

# here will be the database connection

 
# Tries to connect to the MySQL database and retrieves the data from two tables, "orderitems" and "foods", using a SQL query.
# Create a connection to the MySQL database
try:
    cnx = mysql.connector.connect(**config) 
except mysql.connector.Error as err:
    print(f'Error connecting to MySQL database: {err}')
    exit()

cursor = cnx.cursor()
print('Connection is established.')

def recommend_foods(customer_id):
    # Retrieve data from the orderitems and foods tables
    cursor.execute("SELECT o.OrderRef, f.Foodname, o.FoodOrderQunatity FROM orderitems o JOIN foods f ON o.FoodRef = f.FoodID")
    result = cursor.fetchall()

    # Group the data by customer and item
    sales_data = {}
    for row in result:
        customer = row[0]
        item = row[1]
        quantity = row[2]
        if customer not in sales_data:
            sales_data[customer] = {}
        if item not in sales_data[customer]:
            sales_data[customer][item] = 0
        sales_data[customer][item] += quantity

    # Write the results to a CSV file
    with open('sales_data.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['CustomerID', 'Item', 'Quantity'])
        for customer in sales_data:
            for item in sales_data[customer]:
                quantity = sales_data[customer][item]
                writer.writerow([customer, item, quantity])


    # Load the sales data into a pandas dataframe
    sales_data = pd.read_csv('sales_data.csv')

    # Convert the sales data into a matrix where each row represents a customer and each column represents an item
    sales_matrix = sales_data.pivot_table(index='CustomerID', columns='Item', values='Quantity', fill_value=0)

    # Compute the cosine similarity matrix between the customers
    cosine_sim = cosine_similarity(sales_matrix)

    # Define a function that takes in a customer ID and returns the top N items to recommend
    def get_recommendations(customer_id, N):
        # Get the index of the customer in the cosine similarity matrix
        customer_index = sales_matrix.index.get_loc(customer_id)

        # Compute the cosine similarity scores between the customer and all other customers
        scores = list(enumerate(cosine_sim[customer_index]))

        # Sort the scores in descending order
        scores_sorted = sorted(scores, key=lambda x: x[1], reverse=True)

        # Get the indices of the top N most similar customers
        top_indices = [i[0] for i in scores_sorted[1:N+1]]

        # Get the items that the top N customers have purchased
        items = []
        for index in top_indices:
            items += list(sales_matrix.iloc[index].loc[sales_matrix.iloc[index] > 0].index)

        # Get the N most frequently purchased items among the top N customers
        recommendations = pd.Series(items).value_counts().head(N).index.tolist()

        return recommendations

    # Example usage: recommend 5 items for customer 1234
    recommendations = get_recommendations(customer_id, 5)
    print(f"Recommended items for customer {customer_id}: {', '.join(recommendations)}")

def report():
    # Query to retrieve sales data and contribution amounts by provider and time window
    query = '''
        SELECT u.UserName, s.ShowcaseDate, f.Foodname, SUM(oi.FoodOrderQunatity), SUM(oi.FoodOrderQunatity * f.FoodPrice),
            SUM(oi.FoodOrderQunatity * f.FoodPrice * op.PayCharityAmount)
        FROM users u
        JOIN showcase s ON u.UserID = s.UserRef
        JOIN foods f ON s.ShowcaseID = f.FoodshowcaseRef
        JOIN orderitems oi ON f.FoodID = oi.FoodRef
        JOIN `order` o ON oi.OrderRef = o.OrderID AND o.OrderIsCanceled = 0
        JOIN orderpayments op ON o.OrderID = op.OrderRef
        WHERE u.IsSupplier = 1
        GROUP BY u.UserName, s.ShowcaseDate, f.Foodname
    '''

    # Execute the query and fetch the results
    cursor.execute(query)
    results = cursor.fetchall()

    # Process the results to generate the report
    report = {}
    food_performance = {}
    for row in results:
        username = row[0]
        date = row[1].strftime('%Y-%m')
        foodname = row[2]
        quantity = row[3]
        revenue = row[4]
        contribution = row[5]
    
        # Add the sales data and contribution amount to the report
        if username not in report:
            report[username] = {}
        if date not in report[username]:
            report[username][date] = {}
        report[username][date][foodname] = {'quantity': quantity, 'revenue': revenue, 'contribution': contribution}
    
        # Add the sales data to the food performance dictionary
        if foodname not in food_performance:
            food_performance[foodname] = {'quantity': 0, 'revenue': 0}
        food_performance[foodname]['quantity'] += quantity
        food_performance[foodname]['revenue'] += revenue

    # Calculates the threshold values based on the total revenue and quantity of food items sold.
    total_revenue = sum(food_performance[foodname]['revenue'] for foodname in food_performance)
    total_quantity = sum(food_performance[foodname]['quantity'] for foodname in food_performance)
    revenue_threshold = total_revenue * 0.1
    quantity_threshold = total_quantity * 0.1

    # Output the report
    for username in report:
        print(f"Sales performance for {username}:")
        for date in report[username]:
            print(f"\t{date}:")
            total_quantity = 0
            total_revenue = 0
            total_contribution = 0
        
            # Create a list of tuples to sort the food offerings by revenue
            food_tuples = []
            for foodname in report[username][date]:
                quantity = report[username][date][foodname]['quantity']
                revenue = report[username][date][foodname]['revenue']
                contribution = report[username][date][foodname]['contribution']
                food_tuples.append((foodname, revenue, quantity, contribution))
        
            # Sort the food offerings by revenue and output the results
            food_tuples.sort(key=lambda x: x[1], reverse=True)
            for food_tuple in food_tuples:
                foodname, revenue, quantity, contribution = food_tuple
                total_quantity += quantity
                total_revenue += revenue
                total_contribution += contribution
                print(f"\t\t{foodname}: {quantity} sold, ${revenue:.2f} revenue, ${contribution:.2f} contribution")
            
            # Check if there are any underperforming food offerings and output the results
            if len(food_tuples) > 1:
                average_revenue = total_revenue / len(food_tuples)
                underperforming_foods = [food_tuple[0] for food_tuple in food_tuples if food_tuple[1] < average_revenue]
                if underperforming_foods:
                    print("\n\tUnderperforming offerings:")
                    for foodname in underperforming_foods:
                        print(f"\t\t{foodname}")
        
            print(f"\t\tTotal: {total_quantity} sold, ${total_revenue:.2f} revenue, ${total_contribution:.2f} contribution")

def add_user():
    # loop until user enters 'finish'
    while True:
        # get user input
        username = input("Enter username (or 'finish' to exit): ")
        if username == 'finish':
            break
        password = input("Enter password: ")
        firstname = input("Enter firstname: ")
        surname = input("Enter surname: ")
        gender = input("Enter gender: ")
        cell = input("Enter cell: ")
        email = input("Enter email: ")
        is_supplier = input("Is user a supplier? (y/n): ")

        # convert is_supplier to boolean
        if is_supplier.lower() == 'y':
            is_supplier = True
        else:
            is_supplier = False

        # insert user into database
        query = "INSERT INTO users (UserName, UserPassword, UserFirstname, UserSurname, UserGender, UserCell, UserEmail, IsSupplier, UserCreateDate, UserIsActive) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), 1)"
        values = (username, password, firstname, surname, gender, cell, email, is_supplier)
        cursor.execute(query, values)
        cnx.commit()

def add_food():
    # loop until user enters 'finish'
    while True:
        # get user input
        showcase_ref = input("Enter showcase reference ID (or 'finish' to exit): ")
        if showcase_ref == 'finish':
            break
        food_name = input("Enter food name: ")
        food_price = input("Enter food price: ")
        avail_quantity = input("Enter available quantity: ")
        offer_expiry = input("Enter offer expiry date (YYYY-MM-DD): ")
        is_active = input("Is food active? (y/n): ")
        description = input("Enter description: ")
        prep_time = input("Enter preparation time in minutes: ")

        # convert is_active to boolean
        if is_active.lower() == 'y':
            is_active = True
        else:
            is_active = False

        # insert food into database
        query = "INSERT INTO foods (FoodshowcaseRef, Foodname, FoodPrice, AvailQuantity, FoodRegDate, FoodOfferExpiry, FoodIsActive, Description, `PreparationTime(MIN)`) VALUES (%s, %s, %s, %s, NOW(), %s, %s, %s, %s)"
        values = (showcase_ref, food_name, food_price, avail_quantity, offer_expiry, is_active, description, prep_time)
        cursor.execute(query, values)
        cnx.commit()

def select_food(customer_id):
    
    # select all active foods from database
    query = "SELECT FoodID, Foodname FROM foods WHERE FoodIsActive = 1"
    cursor.execute(query)
    foods = cursor.fetchall()

    # display list of foods to user
    print("List of available foods:")
    for food in foods:
        print(f"{food[0]}. {food[1]}")

    # prompt user to select a food
    food_id = input("Enter the ID of the food you want to select: ")
    while not food_id.isdigit() or int(food_id) not in [f[0] for f in foods]:
        food_id = input("Invalid input. Enter the ID of the food you want to select: ")
    food_id = int(food_id)

    # execute recommend_foods function and display recommended foods to user
    recommended_foods = recommend_foods(customer_id)
    print("Recommended foods:")
    for food in recommended_foods:
        print(f"{food[0]}. {food[1]}")

def main():
    while True:
        print('1. Add User')
        print('2. Add Food')
        print('3. Select Food')
        print('4. Report')
        print('5. Exit')
        choice = int(input('Enter your choice(1..4) or exit(5): '))
        if choice == 1:
            add_user()
        elif choice == 2:
            add_food()
        elif choice == 3:
            customerId = input('Enter customer id: ')
            select_food(customerId)
        elif choice == 4:
            report()
        else:
            exit()

if __name__ == '__main__':
    main()