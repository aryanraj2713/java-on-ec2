package com.primechecker;

import java.io.*;
import java.net.*;
import java.util.Arrays;
import java.util.concurrent.Executors;
import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpExchange;

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

    static class PrimeHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String method = exchange.getRequestMethod();
            
            if ("GET".equals(method)) {
                String query = exchange.getRequestURI().getQuery();
                String response;
                
                if (query != null && query.startsWith("numbers=")) {
                    String numbersStr = query.substring(8); // Remove "numbers="
                    try {
                        String[] numberStrs = numbersStr.split(",");
                        int[] numbers = new int[numberStrs.length];
                        for (int i = 0; i < numberStrs.length; i++) {
                            numbers[i] = Integer.parseInt(numberStrs[i].trim());
                        }
                        
                        boolean[] results = arePrime(numbers);
                        response = "Numbers: " + Arrays.toString(numbers) + "\nPrime results: " + Arrays.toString(results);
                    } catch (NumberFormatException e) {
                        response = "Invalid numbers provided. Please use format: ?numbers=2,3,4,5";
                    }
                } else {
                    response = "Prime Checker Service\nUsage: GET /?numbers=2,3,4,5\nHealth: GET /health";
                }
                
                exchange.sendResponseHeaders(200, response.length());
                OutputStream os = exchange.getResponseBody();
                os.write(response.getBytes());
                os.close();
            }
        }
    }

    static class HealthHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String response = "OK";
            exchange.sendResponseHeaders(200, response.length());
            OutputStream os = exchange.getResponseBody();
            os.write(response.getBytes());
            os.close();
        }
    }

    public static void main(String[] args) {
        try {
            int port = 9000;
            
            // If command line args provided, run in CLI mode
            if (args.length > 0) {
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
                return;
            }
            
            // Otherwise, start HTTP server
            HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
            server.createContext("/", new PrimeHandler());
            server.createContext("/health", new HealthHandler());
            server.setExecutor(Executors.newFixedThreadPool(10));
            
            server.start();
            System.out.println("Prime Checker HTTP Server started on port " + port);
            System.out.println("Access at: http://localhost:" + port);
            System.out.println("Health check: http://localhost:" + port + "/health");
            System.out.println("Example: http://localhost:" + port + "/?numbers=2,3,4,5");
            
            // Keep the server running
            Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                System.out.println("Shutting down server...");
                server.stop(0);
            }));
            
        } catch (Exception e) {
            System.err.println("Failed to start server: " + e.getMessage());
            e.printStackTrace();
        }
    }
} 