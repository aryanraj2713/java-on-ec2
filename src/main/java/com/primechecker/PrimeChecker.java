package com.primechecker;

import java.util.Arrays;

public class PrimeChecker {

    public static boolean isPrime(int n) {
        if (n <= 1) {
            return false;
        }
        for (int i = 2; i * i <= n; i++) {
            if (n % i == 0) {
                return false;
            }
        }
        return true;
    }

    public static boolean[] arePrime(int[] numbers) {
        boolean[] results = new boolean[numbers.length];
        for (int i = 0; i < numbers.length; i++) {
            results[i] = isPrime(numbers[i]);
        }
        return results;
    }

    public static void main(String[] args) {
        if (args.length == 0) {
            System.out.println("Please provide a list of numbers as command-line arguments.");
            return;
        }

        int[] numbers = new int[args.length];
        for (int i = 0; i < args.length; i++) {
            try {
                numbers[i] = Integer.parseInt(args[i]);
            } catch (NumberFormatException e) {
                System.err.println("Invalid number: " + args[i]);
                return;
            }
        }

        boolean[] primeResults = arePrime(numbers);
        System.out.println("Are the numbers prime?");
        System.out.println(Arrays.toString(primeResults));
    }
} 