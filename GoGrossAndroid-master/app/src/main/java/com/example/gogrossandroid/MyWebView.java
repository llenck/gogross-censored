package com.example.gogrossandroid;

import static android.content.ContentValues.TAG;

import android.annotation.SuppressLint;
import android.app.DownloadManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;

import android.util.Log;
import android.view.KeyEvent;
import android.view.View;
import android.webkit.DownloadListener;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.activity.EdgeToEdge;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import android.webkit.CookieManager;
import android.widget.Toast;

import com.google.android.material.snackbar.BaseTransientBottomBar;
import com.google.android.material.snackbar.Snackbar;

public class MyWebView extends AppCompatActivity {

    SharedPreferences sharedPreferences;
    android.webkit.WebView myWebView;
    String url;
    CookieManager cookieManager;

    String savedCookies = null;
    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_web_view);

        hideUI();

        myWebView = findViewById(R.id.webView);
        myWebView.getSettings().setJavaScriptEnabled(true);
        Intent intent = getIntent();
        url = intent.getStringExtra("link");
        myWebView.setWebViewClient(new WebViewClient() {

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String link = request.getUrl().toString();
                if (link.contains("invoice?id")) {
                    // Download the PDF file
                    downloadPdf(link);
                    return true; // We handled the URL loading
                }

                // For other URLs, allow the WebView to handle them
                return super.shouldOverrideUrlLoading(view, request);
            }

            private void downloadPdf(String url) {
                // Create a DownloadManager request for the PDF file
                DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
                // Get session cookies from the CookieManager
                String sessionCookie = cookieManager.getCookie(url);

                // Add session cookie to the request headers
                if (sessionCookie != null) {
                    request.addRequestHeader("Cookie", sessionCookie);
                }
                request.setTitle("PDF Download"); // Set title for the download notification
                request.setDescription("Downloading PDF..."); // Set description for the download notification

                // Specify the directory where the PDF file will be downloaded
                // For example, to download to the Downloads directory:
                request.setDestinationInExternalPublicDir(android.os.Environment.DIRECTORY_DOWNLOADS, "invoice.pdf");

                // Enqueue the download request
                DownloadManager downloadManager = (DownloadManager) getSystemService(MyWebView.DOWNLOAD_SERVICE);
                if (downloadManager != null) {
                    downloadManager.enqueue(request);
                    Snackbar mySnackbar = Snackbar.make(myWebView, "Invoice is downloaded, you can open it in your files", BaseTransientBottomBar.LENGTH_SHORT);
                    mySnackbar.show();
                }
            }
        });

        cookieManager = CookieManager.getInstance();
        cookieManager.setAcceptCookie(true);
        cookieManager.acceptThirdPartyCookies(myWebView);



        sharedPreferences = getSharedPreferences("MyPrefs", MODE_PRIVATE);

        loadCookies();

        myWebView.loadUrl(url);
    }

    private void loadCookies() {
        try {
            savedCookies = sharedPreferences.getString("saved_cookies",null);
        }catch (Exception e){
            e.printStackTrace();
        }
        if (savedCookies != null) {
            CookieManager.getInstance().setCookie(url, savedCookies);
        }
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (event.getAction() == KeyEvent.ACTION_DOWN) {
            switch (keyCode) {
                case KeyEvent.KEYCODE_BACK:
                    if (myWebView.canGoBack()) {
                        myWebView.goBack();
                    } else {
                        finish();
                    }
                    return true;
            }
        }
        return super.onKeyDown(keyCode, event);
    }

    private void hideUI(){
        View view = findViewById(R.id.main);
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        WindowInsetsControllerCompat controller = new WindowInsetsControllerCompat(getWindow(), view);
        controller.hide(WindowInsetsCompat.Type.systemBars());
        controller.setSystemBarsBehavior(WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);

        ViewCompat.setOnApplyWindowInsetsListener(view, (v, insets) -> {
            Insets systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom);
            return insets;
        });
    }

    private void saveCookies() {
        // Capture cookies using CookieManager
        String cookies = CookieManager.getInstance().getCookie(url);
        Log.e(TAG, "All cookies: " + cookies);
        // Save cookies to SharedPreferences
        SharedPreferences.Editor editor = sharedPreferences.edit();
        editor.putString("saved_cookies", cookies);
        editor.apply();
    }
}
