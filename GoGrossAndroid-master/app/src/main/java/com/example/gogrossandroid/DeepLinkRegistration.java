package com.example.gogrossandroid;

import android.content.Intent;
import android.os.AsyncTask;
import android.os.Bundle;
import android.view.View;
import android.widget.EditText;
import android.widget.TextView;

import androidx.activity.EdgeToEdge;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;

import com.google.android.material.snackbar.BaseTransientBottomBar;
import com.google.android.material.snackbar.Snackbar;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.lang.ref.WeakReference;
import java.net.HttpURLConnection;
import java.net.URL;

public class DeepLinkRegistration extends AppCompatActivity {

    private String link = "";
    private String permaLink = "";
    private static View view;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_deep_link_registration);
        // Hide system UI and adjust insets
        hideSystemUI();

        findViewById(R.id.register).setOnClickListener(view -> {
            EditText linkField = findViewById(R.id.linkText);
            link = linkField.getText().toString();
            LinkValidationTask validationTask = new LinkValidationTask(this, link);
            validationTask.execute(link);
        });

        findViewById(R.id.lastLink).setOnClickListener(view -> changeActivity(permaLink));
    }

    @Override
    protected void onResume() {
        super.onResume();
        loadContent();
        TextView lastLink = findViewById(R.id.lastLink);
        //lastLink.setText(permaLink);
        lastLink.setVisibility(permaLink.isEmpty() ? View.GONE : View.VISIBLE);
    }

    private void hideSystemUI() {
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        WindowInsetsControllerCompat controller = new WindowInsetsControllerCompat(getWindow(), findViewById(R.id.main));
        controller.hide(WindowInsetsCompat.Type.systemBars());
        controller.setSystemBarsBehavior(WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);

        view = findViewById(R.id.main);
        ViewCompat.setOnApplyWindowInsetsListener(view, (v, insets) -> {
            Insets systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom);
            return insets;
        });
    }

    // Function to read the last used String from our generated File
    public void loadContent(){
        File path = getApplicationContext().getFilesDir();
        File readFrom = new File(path, "lastLink.txt");
        byte[] content = new byte[(int) readFrom.length()];

        FileInputStream stream = null;
        try {
            stream = new FileInputStream(readFrom);
            stream.read(content);

            String stringContent = new String(content);
            permaLink = stringContent;
        }catch (Exception e){
            e.printStackTrace();
        }
    }
    // Overwrite and adjust onDestroy function to create a new file containing the last used Link
    protected void saveContent(){
        File path = getApplicationContext().getFilesDir();
        try {
            FileOutputStream writer = new FileOutputStream(new File(path, "lastLink.txt"));
            writer.write(link.getBytes());
        }catch (Exception e){
            e.printStackTrace();
        }
    }
    protected void changeActivity(String string){
        Intent intent = new Intent(DeepLinkRegistration.this, MyWebView.class);
        intent.putExtra("link", string);
        startActivity(intent);
    }

    static void displayErrorMessage(String message) {
        Snackbar mySnackbar = Snackbar.make(view, message, BaseTransientBottomBar.LENGTH_SHORT);
        mySnackbar.show();
    }
}
