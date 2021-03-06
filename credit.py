def main():
    number = int(input("Number: "))

    luhn(number)

def luhn(number):

    count = 0
    digits = 0
    underlinedigits = 0
    amex = False
    visa = False
    mastercard = False

    while(number != 0):
        # start analysing the digits from the left
        # if count is even, don't multiply that digit by 2
        # if count is odd, multiply that digit by 2
        if count%2 == 0:
            digits += number%10
        else:
            calc = (number%10)*2
            if calc < 10:
                underlinedigits += calc
            else:
                underlinedigits = int(calc/10) + calc%10 + underlinedigits

        if number == 34 or number == 37:
            amex = True
        elif number in range(51, 56):
            mastercard = True
        elif number == 4:
            visa = True

        number = int(number/10);
        count+=1

        print(number)
        print(count)

    result = digits + underlinedigits
    result = int(result%10)
    print(result)

    if (result == 0):
        if count == 13 and visa == True:
            print("VISA")
            return(True)
        elif count == 15 and amex == True:
            print("AMEX")
            return(True)
        elif count == 16 and visa == True:
            print("VISA")
            return(True)
        elif count == 16 and mastercard == True:
            print("MASTERCARD")
            return(True)
        else:
            print("INVALID")
            return(False)
    else:
        print("INVALID")
        return(False)


if __name__ == '__main__':
    main()