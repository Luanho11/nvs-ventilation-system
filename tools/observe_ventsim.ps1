# Ayudantes de OBSERVACIÓN de la aplicación de referencia en ejecución (solo lectura de la interfaz).
# Uso:  . .\tools\observe_ventsim.ps1 ; Get-VsWindow ; Dump-Msaa <hwnd> 5 ; Save-WindowShot <hwnd> ruta.png ; Get-ComboItems <hwnd>
# - Dump-Msaa: árbol de accesibilidad MSAA (menús, botones, nombres, orden, jerarquía).
# - Save-WindowShot: captura SOLO la ventana indicada (PrintWindow), nunca el escritorio.
# No inyecta código, no lee memoria, no modifica la aplicación ni sus archivos.
Add-Type -AssemblyName System.Drawing

$srcMsaa = @"
using System; using System.Collections.Generic; using System.Runtime.InteropServices; using System.Text; using Accessibility;
public class Msaa2 {
  [DllImport("oleacc.dll")] static extern int AccessibleObjectFromWindow(IntPtr hwnd, uint id, ref Guid iid, [MarshalAs(UnmanagedType.Interface)] out object ppv);
  [DllImport("oleacc.dll")] static extern int AccessibleChildren(IAccessible paccContainer, int iChildStart, int cChildren, [Out] object[] rgvarChildren, out int pcObtained);
  [DllImport("oleacc.dll")] static extern uint GetRoleText(uint role, StringBuilder sb, uint n);
  static Guid IID = new Guid("618736E0-3C3D-11CF-810C-00AA00389B71");
  static string Role(object r) { try { if (r is int) { var sb=new StringBuilder(64); GetRoleText((uint)(int)r, sb, 64); return sb.ToString(); } return Convert.ToString(r);} catch { return "?"; } }
  static void Dump(IAccessible acc, object child, int depth, int max, List<string> o) {
    if (depth > max) return;
    string name="", role="", desc="", kb="", state="";
    try { name = acc.get_accName(child); } catch {}
    try { role = Role(acc.get_accRole(child)); } catch {}
    try { desc = acc.get_accDescription(child); } catch {}
    try { kb = acc.get_accKeyboardShortcut(child); } catch {}
    try { state = Convert.ToString(acc.get_accState(child)); } catch {}
    int x=0,y=0,w=0,h=0; try { acc.accLocation(out x, out y, out w, out h, child); } catch {}
    o.Add(new string(' ', depth*2) + role + " | '" + name + "' | desc='" + desc + "' | kb='" + kb + "' | st=" + state + " | " + x+","+y+","+w+","+h);
    if (child is int && (int)child != 0) return;
    int cnt = 0; try { cnt = acc.accChildCount; } catch {}
    if (cnt <= 0) return;
    var arr = new object[cnt]; int got;
    if (AccessibleChildren(acc, 0, cnt, arr, out got) != 0) return;
    for (int i=0;i<got;i++) { var c = arr[i]; if (c is int) Dump(acc, c, depth+1, max, o); else if (c is IAccessible) Dump((IAccessible)c, 0, depth+1, max, o); }
  }
  // Invoca (acción por defecto) el elemento cuyo camino de nombres se indica, p. ej. Archivo > Cargar demostración > Mina de metal.
  static bool Find(IAccessible acc, string[] path, int i) {
    int cnt = 0; try { cnt = acc.accChildCount; } catch { return false; }
    var arr = new object[cnt]; int got; if (AccessibleChildren(acc, 0, cnt, arr, out got) != 0) return false;
    for (int k = 0; k < got; k++) {
      var c = arr[k]; IAccessible owner = acc; object id = 0; IAccessible node = null;
      if (c is int) { id = c; } else if (c is IAccessible) { node = (IAccessible)c; owner = node; id = 0; } else continue;
      string name = ""; try { name = owner.get_accName(id); } catch {}
      if (name == path[i]) {
        if (i == path.Length - 1) { try { owner.accDoDefaultAction(id); return true; } catch { return false; } }
        if (node != null && Find(node, path, i + 1)) return true;
        if (node == null && Find(acc, path, i + 1)) return true;
      } else if (node != null && i == 0 && Find(node, path, 0)) return true;
    }
    return false;
  }
  public static bool Invoke(long hwnd, string[] path) {
    object obj; int r = AccessibleObjectFromWindow(new IntPtr(hwnd), 0xFFFFFFFC, ref IID, out obj);
    if (r != 0 || obj == null) return false; return Find((IAccessible)obj, path, 0);
  }
  public static List<string> DumpHwnd(long hwnd, int max) {
    var o = new List<string>(); object obj; int r = AccessibleObjectFromWindow(new IntPtr(hwnd), 0xFFFFFFFC, ref IID, out obj);
    if (r != 0 || obj == null) { o.Add("sin IAccessible (hr=" + r + ")"); return o; }
    Dump((IAccessible)obj, 0, 0, max, o); return o;
  }
}
"@
Add-Type -TypeDefinition $srcMsaa -ReferencedAssemblies Accessibility

$srcCap = @"
using System; using System.Collections.Generic; using System.Drawing; using System.Runtime.InteropServices; using System.Text;
public class Cap {
  [DllImport("user32.dll")] static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, StringBuilder l);
  [DllImport("user32.dll")] static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr p, EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
  public static bool Save(IntPtr h, string path) {
    RECT r; GetWindowRect(h, out r); int w=r.R-r.L, hh=r.B-r.T; if (w<=0||hh<=0) return false;
    using (var bmp = new Bitmap(w, hh)) { using (var g = Graphics.FromImage(bmp)) { IntPtr dc = g.GetHdc(); PrintWindow(h, dc, 2); g.ReleaseHdc(dc); } bmp.Save(path); }
    return true;
  }
  public static List<string> ComboItems(long h) {
    var r=new List<string>(); int n=(int)SendMessage(new IntPtr(h),0x146,IntPtr.Zero,IntPtr.Zero); r.Add("count="+n);
    for(int i=0;i<n&&i<120;i++){ var sb=new StringBuilder(256); SendMessage(new IntPtr(h),0x148,new IntPtr(i),sb); r.Add("  ["+i+"] "+sb); }
    r.Add("sel="+(int)SendMessage(new IntPtr(h),0x147,IntPtr.Zero,IntPtr.Zero)); return r;
  }
  public static List<string> Children(IntPtr parent) {
    var l=new List<string>(); EnumChildWindows(parent,(h,x)=>{ var c=new StringBuilder(128); GetClassName(h,c,128); RECT r; GetWindowRect(h,out r); l.Add(h.ToInt64()+"|"+c+"|vis="+IsWindowVisible(h)+"|"+r.L+","+r.T+","+(r.R-r.L)+","+(r.B-r.T)); return true;},IntPtr.Zero); return l;
  }
}
"@
Add-Type -TypeDefinition $srcCap -ReferencedAssemblies System.Drawing

function Get-VsWindow { $p = Get-Process VVentsim -ErrorAction SilentlyContinue; if ($p) { $p.Refresh(); $p.MainWindowHandle } }
function Dump-Msaa([long]$hwnd, [int]$depth = 4) { [Msaa2]::DumpHwnd($hwnd, $depth) }
function Save-WindowShot([long]$hwnd, [string]$path) { [Cap]::Save([IntPtr]$hwnd, $path) }
function Get-ComboItems([long]$hwnd) { [Cap]::ComboItems($hwnd) }
function Get-ChildWindows([long]$hwnd) { [Cap]::Children([IntPtr]$hwnd) }
function Invoke-Msaa([long]$hwnd, [string[]]$path) { [Msaa2]::Invoke($hwnd, $path) }
