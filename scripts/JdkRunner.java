// Reads lines of base64(pattern) \t base64(replacement) \t base64(input) on stdin and
// writes one line per case: "OK <base64(output)>" or "ERR <base64(message)>".
// Run with the JDK single-file launcher: java scripts/JdkRunner.java
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.regex.Pattern;

public class JdkRunner {
    public static void main(String[] args) throws IOException {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        PrintStream out = new PrintStream(System.out, true, StandardCharsets.UTF_8);
        Base64.Decoder dec = Base64.getDecoder();
        Base64.Encoder enc = Base64.getEncoder();
        String line;
        while ((line = in.readLine()) != null) {
            String[] f = line.split("\t", -1);
            String pat = new String(dec.decode(f[0]), StandardCharsets.UTF_8);
            String rep = new String(dec.decode(f[1]), StandardCharsets.UTF_8);
            String txt = new String(dec.decode(f[2]), StandardCharsets.UTF_8);
            try {
                String r = Pattern.compile(pat).matcher(txt).replaceAll(rep);
                out.println("OK " + enc.encodeToString(r.getBytes(StandardCharsets.UTF_8)));
            } catch (Exception e) {
                out.println("ERR " + enc.encodeToString(String.valueOf(e.getMessage()).getBytes(StandardCharsets.UTF_8)));
            }
        }
    }
}
